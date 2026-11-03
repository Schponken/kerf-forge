# Files & guides: making handoff

Scope: `renderFiles`, file/guide naming helpers, `.files-handoff` / `.handoff-*` styles and a mocked browser fixture.
Mode: Operate. The user requested an object-first studio with an intentional, quiet interface. First-time noncoder
comprehension is a design lens; no audience interview or claim of observed conversion is implied.

Six selected improvements:

1. Put saved build context beside the download decision, keeping incomplete, failed, stale, running and paused
   evidence explicit. Reuse the project's status interpretation and existing Checks / Build kit actions.
2. Lead with the assembly guide, shopping list and print settings. Reading a guide and downloading its original
   file remain distinct actions; design notes and source references remain available in a disclosure.
3. State that purchased components are separate from printed parts. A missing shopping list means the quantities
   are unavailable, never that all parts can be printed or no purchase is necessary.
4. Organize downloads by the maker's task, including plate, individual part, drawing, supplier, CAD, firmware and
   simulation outputs. Unknown future file types remain downloadable. Guide-only projects no longer lose documents.
5. Keep file groups compact with native, keyboard-accessible disclosures, focus restoration across refresh, Escape
   close, short progressive-enhancement size transitions and reduced-motion support. Phone layout becomes one column.
6. Make source/output provenance inspectable: original names and paths, saved record time and fingerprint, build
   warnings, source guides and the existing project ZIP. The API does not establish an individual file's build match;
   say so visibly and never label a file current or print-ready based solely on a successful saved check record.

The shared design contract is the studio-shell worktree's DESIGN.md: system face, existing semantic theme tokens,
8px controls, thin rules, no decorative icons/cards/gradients. This change does not edit shared header or shell rules.

Validation uses only mocked API responses and synthetic output names; no real project, geometry build, app job,
paid agent, printer or stress check. Browser assertions retain every listed file/document and exercise both themes
at 1512×982 and 390×844. Integration owns the final combined shell/viewer visual proof. Source export backend
PRs remain separate; this change uses the existing ZIP endpoint without duplicating their logic.

Bounded visual review: first capture batch showed readable guide/file separation and no horizontal overflow in
both themes and both sizes. Correction: reading controls now have a persistent link affordance, and filename-based
focus IDs are URL-encoded. The existing render lightbox is preserved with a keyboard-accessible link. Native details
transitions are a progressive enhancement; unsupported browsers retain functional native opening/closing.
The mechanical scan reports the pre-existing global styling plus the deliberate 160ms intrinsic-height disclosure
transition; it is limited to user-opened groups, with no entrance replay on refresh and no reduced-motion transition.
