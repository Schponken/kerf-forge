# Kerf Studio

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Spencer uses Kerf to turn design requests into engineered, printable assemblies and inspect the work in progress.
The requested redesign uses a first-time, noncoder client lens. Broader audience research has not been conducted;
do not present that design assumption as an interview finding.

## Product Purpose

Studio provides the local interface for describing designs, choosing researched options, viewing and tuning
projects, reading checks and build files, and following work performed by Kerf and its connected coding agents.
Success means understanding the current state and finding the next appropriate action without reading source code.

## Operating Context

The existing HTML/CSS/JavaScript application is served by `kerf/studio.py`. It runs in a browser and in the macOS
WKWebView wrapper. Projects contain CAD sources and engineering requirements; the interface distinguishes
unbuilt, running, failed, paused, stale and completed work. Work can span local jobs and shared repository claims.

## Capabilities and Constraints

- Preserve current navigation, projects, saved options, parameters, materials, builds, reports and job controls.
- Follow live can show geometry updates without proving engineering checks; preserve that distinction.
- Status must describe observed evidence. Unknown progress and time estimates stay unknown.
- Printing is opt-in. Paused stress checks do not prove strength. Visual changes must not alter these safeguards.
- Synthetic visual fixtures must remain clearly identified; do not invent finished projects or measured results.

## Brand Commitments

The product name is Kerf Studio. The user explicitly authorized replacing the visual identity, asked for fewer
AI-looking gradients, fonts and placements, and delegated routine design decisions. No orange palette, decorative
background or custom font is a binding brand requirement.

## Evidence on Hand

Existing Studio code, user screenshots, repository workflows in CLAUDE.md, and synthetic browser fixtures.
There are no supplied audience interviews, testimonials or product-performance benchmarks.

## Product Principles

1. Make the next action and its scope clear.
2. Keep project content and evidence ahead of decorative interface chrome.
3. Preserve uncertainty and distinguish ownership from actual execution.
4. Keep navigation and controls usable by keyboard and on narrow screens.
