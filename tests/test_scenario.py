"""Scenario choices carry evidence and cannot silently become a build or purchase."""
import copy
import json
from types import SimpleNamespace

import pytest

from kerf import quotes, studio
from test_studio import _browser, _post, server  # noqa: F401


@pytest.fixture
def comparison():
    # Illustrative data, not product advice or an E8 engineering result.
    buy = {"title": "Ready-made watering kit", "summary": "A complete watering kit to evaluate.", "route": "buy",
           "parts_printed": 0, "cost_usd": None, "print_hours": 0,
           "cost_note": "A current delivered price has not been checked.", "print_note": "No printed parts.",
           "fit": "Confirm that its capacity covers six plants for ten days.",
           "effort": "Set up and observe a trial before traveling; timing is not yet measured.",
           "risks": ["A leak could damage the floor."], "next_steps": ["Check capacity and current availability."],
           "sources": [{"title": "Illustrative source", "url": "https://example.com/watering",
                        "finding": "Test fixture only; no product research is claimed."}]}
    build = {**copy.deepcopy(buy), "title": "Adapt a reservoir mount", "route": "adapt", "parts_printed": 1,
             "print_hours": None, "print_note": "Geometry has not been sized or sliced.",
             "fit": "A custom mount may fit the shelf; water demand still needs measuring."}
    return {"request_kind": "scenario", "options": [buy, build], "recommended": 0,
            "recommendation_reason": "Start with the kit if its capacity is sufficient: less hands-on work.",
            "assumptions": ["Indoor use."], "questions": []}


def test_comparison_preserves_unknowns_and_requires_both_routes(comparison):
    assert quotes.validate(comparison)["options"][0]["cost_usd"] is None
    comparison["options"][0]["route"] = "build"
    with pytest.raises(ValueError, match="buy option"):
        quotes.validate(comparison)


@pytest.mark.parametrize("field,value,error", [
    ("cost_usd", -1, "cost_usd"), ("cost_usd", float("nan"), "cost_usd"), ("cost_usd", 10**400, "cost_usd"),
    ("print_hours", float("inf"), "print_hours"), ("parts_printed", True, "parts_printed"),
    ("parts_printed", 1.5, "whole number"), ("cost_note", "", "cost_usd"),
    ("fit", "", "fit"), ("risks", "risk", "list"), ("sources", [], "research sources"),
    ("purchased", [{"key": "servos.SG90", "qty": -1}], "quantity"),
])
def test_invalid_evidence_does_not_become_a_quote(comparison, field, value, error):
    comparison["options"][0][field] = value
    with pytest.raises(ValueError, match=error):
        quotes.validate(comparison)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,hi", "https://name:secret@example.com/",
                                 "https://example.com/\nhello", "https:///no-host", "https://[bad"])
def test_sources_cannot_be_active_content_or_credentials(comparison, url):
    comparison["options"][0]["sources"][0]["url"] = url
    with pytest.raises(ValueError, match="source URL"):
        quotes.validate(comparison)


@pytest.mark.parametrize("index", [True, -1, 2, "0"])
def test_recommendation_must_select_an_existing_option(comparison, index):
    comparison["recommended"] = index
    with pytest.raises(ValueError, match="recommended"):
        quotes.validate(comparison)


@pytest.fixture
def saved_quote(tmp_path, monkeypatch, comparison):
    monkeypatch.setattr(studio, "QUOTES", tmp_path)
    monkeypatch.setattr(studio, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(studio, "claude_ready", lambda: {"ok": True})
    monkeypatch.setattr(studio, "claude_bin", lambda: "claude")
    context = {"description": "my plants die when I travel", "intake": {"request_kind": "scenario",
               "success": "six plants, ten days", "priority": "Reliability and low maintenance"}}
    (tmp_path / "plants.json").write_text(json.dumps(comparison))
    (tmp_path / "plants.request.json").write_text(json.dumps(context))
    return context


def test_saved_context_enforces_scenario_contract(tmp_path, saved_quote):
    legacy = {"options": [{"title": "A", "summary": "s", "parts_printed": 1, "cost_usd": 1, "print_hours": 1}]}
    (tmp_path / "plants.json").write_text(json.dumps(legacy))
    with pytest.raises(ValueError, match="2-3"):
        studio.read_quote("plants")


def test_design_uses_saved_option_not_client_object(saved_quote, monkeypatch):
    calls = []
    monkeypatch.setattr(studio, "start_job", lambda *args, **kwargs: calls.append((args, kwargs)))
    studio.new_design("plants", **saved_quote, option={"title": "FORGED"}, option_index=1)
    prompt = calls[0][0][2][2]
    assert "FORGED" not in prompt
    assert "Adapt a reservoir mount" in prompt and "https://example.com/watering" in prompt
    assert "six plants, ten days" in prompt and "Do not buy anything" in prompt


def test_buy_stale_and_unresolved_options_never_start_a_job(saved_quote, monkeypatch, comparison, tmp_path):
    calls = []
    monkeypatch.setattr(studio, "start_job", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match="buy-only"):
        studio.new_design("plants", **saved_quote, option_index=0)
    with pytest.raises(ValueError, match="compare options first"):
        studio.new_design("plants", **saved_quote)
    with pytest.raises(ValueError, match="request changed"):
        studio.new_design("plants", saved_quote["description"] + " outdoors", saved_quote["intake"], option_index=1)
    comparison["questions"] = ["How much water do the plants use each day?"]
    (tmp_path / "plants.json").write_text(json.dumps(comparison))
    with pytest.raises(ValueError, match="open questions"):
        studio.new_design("plants", **saved_quote, option_index=1)
    assert not calls and not (studio.PROJECTS / "plants").exists()


def test_api_resolves_buy_choice_on_server(server, saved_quote, monkeypatch):
    calls = []
    monkeypatch.setattr(studio, "start_job", lambda *args, **kwargs: calls.append(args))
    status, result = _post(server + "/api/new", {"name": "plants", **saved_quote, "option_index": 0,
                                               "option": {"route": "build"}})
    assert status == 400 and "buy-only" in result["error"]
    assert not calls


def test_quote_prompt_and_context_are_prepared_under_job_lock(tmp_path, monkeypatch, saved_quote):
    jobs = {}
    monkeypatch.setattr(studio, "JOBS", jobs)
    monkeypatch.setattr(studio, "Job", lambda *args, **kwargs: SimpleNamespace(id="quote", state="running",
                       project=args[1], label=args[3], cmd=args[2]))
    job = studio.quote("plants", **saved_quote)
    assert "SCENARIO OPTIONS" in job.cmd[2] and "Unknown prices/times stay null" in job.cmd[2]
    assert json.loads((tmp_path / "plants.request.json").read_text()) == saved_quote
    out = tmp_path / "plants.json"
    out.write_text("in progress")
    with pytest.raises(ValueError, match="already running"):
        studio.quote("plants", "changed request", {"request_kind": "scenario"})
    assert out.read_text() == "in progress"
    assert json.loads((tmp_path / "plants.request.json").read_text()) == saved_quote


def test_scenario_browser_compares_buy_and_adapt_without_fake_zero(server, saved_quote, tmp_path):
    out = _browser(server + "/", """
await p.route('**/api/claude', r => r.fulfill({json: {ok:true}}));
await p.click('#newbtn'); await p.selectOption('#i_request_kind', 'scenario');
out.scenario = await p.isVisible('#scenario-fields'); out.direct = await p.isVisible('#nstart');
await p.fill('#nname', 'plants'); await p.evaluate(() => showQuote('plants')); await p.waitForSelector('.qopt');
out.unknown = await p.locator('.qopt').first().innerText();
out.buyButtons = await p.locator('.qopt').first().locator('button').count();
out.source = await p.locator('.qopt a').first().getAttribute('rel');
await p.locator('.qopt a').first().focus();
out.sourceFocused = await p.evaluate(() => document.activeElement.tagName === 'A');
out.buildDisabled = await p.locator('.qopt').nth(1).locator('button').isDisabled();
out.restored = await p.inputValue('#ndesc');
out.layout = [];
for (const width of [1300, 390]) {
  await p.setViewportSize({width,height:900});
  out.layout.push(await p.evaluate(() => document.querySelector('#main').scrollWidth <= document.querySelector('#main').clientWidth));
  if(width === 390) out.overflow = await p.evaluate(() => [...document.querySelectorAll('#main *')].filter(e=>e.getBoundingClientRect().right>390).map(e=>[e.tagName,e.className,e.id,e.getBoundingClientRect().right]).slice(0,20));
}
await p.fill('#i_success', 'new requirement'); await p.evaluate(() => showQuote('plants'));
out.changedDisabled = await p.locator('.qopt').nth(1).locator('button').isDisabled();
out.keptEdit = await p.inputValue('#i_success');
""", tmp_path)
    assert out["errs"] == [] and out["scenario"] and not out["direct"], out
    assert "Cost not yet known" in out["unknown"] and "$0" not in out["unknown"]
    assert out["buyButtons"] == 0 and out["source"] == "noopener noreferrer" and out["sourceFocused"]
    assert not out["buildDisabled"] and out["restored"] == saved_quote["description"]
    assert all(out["layout"]), out.get("overflow")
    assert out["changedDisabled"] and out["keptEdit"] == "new requirement", out
