# Implementation Plan: TypeScript client SDK

## Summary

Create `@swedev/klartex` npm package in a new repo (`swedev/klartex-js`) -- a typed fetch wrapper around the Klartex HTTP API. The package provides three methods: `render()` for PDF generation, `templates()` for listing available templates, and `schema()` for retrieving JSON Schema definitions.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | None |
| **Blocks** | None |
| **Related issues** | #4 Docker image (provides the server this SDK talks to) |
| **Scope** | ~12 new files in a new repo |
| **Risk** | Low |
| **Complexity** | Low |
| **Safe for junior** | Yes |
| **Conflict risk** | Low -- entirely new repo, no overlap with existing plans |
| **External dependencies** | npm `@swedev` scope ownership, GitHub repo creation permission |

### Triage Notes

This is a greenfield package with no dependencies on other open issues. However, it is most useful once the HTTP API is running (e.g., via Docker image from #4). The API surface is already stable -- three endpoints: `POST /render`, `GET /templates`, `GET /templates/{name}/schema`. Repo creation and npm scope access are prerequisites but assumed available to the repo owner.

## Analysis

The Klartex HTTP API (FastAPI in `klartex/main.py`) exposes three endpoints:

1. **`POST /render`** -- Accepts `{ template, data, branding?, branding_dir? }`, returns PDF bytes (`application/pdf`)
2. **`GET /templates`** -- Returns `[{ name, description }]`
3. **`GET /templates/{name}/schema`** -- Returns JSON Schema object

The SDK should be a thin typed wrapper using `fetch` (no external HTTP dependencies) to keep it lightweight. Following the pattern established in `@svensk/*` packages: TypeScript + tsup + vitest, dual CJS/ESM output.

### API field mapping

The HTTP API uses snake_case (`branding_dir`) while the TypeScript SDK should use camelCase (`brandingDir`). The client must map camelCase options to snake_case in the request body.

## Implementation Steps

### Phase 1: Project Setup

1. Create new repo `swedev/klartex-js`
   - Initialize with `npm init`
   - Package name: `@swedev/klartex`
2. Set up TypeScript configuration
   - `tsconfig.json` following `@svensk/pernum` pattern
   - Target: ES2022 (Node 18+ for native fetch)
3. Set up build tooling
   - `tsup` for dual CJS/ESM builds with `.d.ts` generation
   - `vitest` for testing
4. Create project files:
   - `package.json` with proper `exports`, `types`, `main`, `module`, `engines` fields
   - `tsconfig.json`
   - `.gitignore`
   - `README.md` (Swedish) + `README.en.md`

### Phase 2: Core Implementation

1. Create `src/index.ts` -- main entry point, exports `createClient` and all types
2. Create `src/types.ts` -- TypeScript type definitions
   - `KlartexOptions` -- client config (`baseUrl`, custom `fetch`, extra `headers`)
   - `RenderOptions` -- optional fields: `branding?`, `brandingDir?`
   - `TemplateInfo` -- `{ name: string, description: string }`
3. Create `src/errors.ts` -- error classes
   - `KlartexError` -- base error class
   - `KlartexHttpError` extends `KlartexError` -- with `status`, `statusText`, and `body`
4. Create `src/client.ts` -- the client implementation
   - `createClient(options: KlartexOptions)` returns `KlartexClient`
   - `client.render(template: string, data: Record<string, unknown>, options?: RenderOptions)` -> `Promise<ArrayBuffer>`
   - `client.templates()` -> `Promise<TemplateInfo[]>`
   - `client.schema(name: string)` -> `Promise<Record<string, unknown>>`
   - Internal: normalize `baseUrl` (strip trailing slash), map camelCase to snake_case for request body

### Phase 3: Testing

1. Create `test/client.test.ts`
   - Unit tests using mocked fetch (inject via `KlartexOptions.fetch`)
   - Test `render()` sends correct POST body and returns ArrayBuffer
   - Test `templates()` returns typed array
   - Test `schema(name)` returns JSON object
   - Test error handling: 400 (validation), 404 (not found), 500 (server error)
   - Test non-JSON error response bodies
   - Test `brandingDir` maps to `branding_dir` in request body
   - Test trailing slash in `baseUrl` is normalized
   - Test custom headers are passed through
   - Test network/fetch failure throws `KlartexError`

### Phase 4: Documentation

1. Write `README.md` (Swedish, primary) with usage examples
2. Write `README.en.md` (English mirror)
3. Add `LICENSE` (MIT)

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `package.json` | Create | Package manifest with @swedev/klartex name, exports, types, engines |
| `tsconfig.json` | Create | TypeScript config (ES2022, strict) |
| `.gitignore` | Create | Ignore node_modules, dist |
| `src/index.ts` | Create | Public API entry point -- re-exports createClient and types |
| `src/types.ts` | Create | TypeScript type definitions (KlartexOptions, RenderOptions, TemplateInfo) |
| `src/errors.ts` | Create | Error classes (KlartexError, KlartexHttpError) |
| `src/client.ts` | Create | Client implementation with fetch wrapper |
| `test/client.test.ts` | Create | Unit tests with mocked fetch |
| `README.md` | Create | Swedish documentation |
| `README.en.md` | Create | English documentation |
| `LICENSE` | Create | MIT license |

## Codebase Areas

- New repo `swedev/klartex-js` (all new files, no overlap with existing code)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Separate Repo

**Options:** (A) New repo `swedev/klartex-js` vs. (B) `sdk/` directory in the Python klartex repo
**Decision:** A -- separate repo
**Rationale:** Keeps Python and TypeScript ecosystems cleanly separated. The Python repo uses `pyproject.toml` / hatchling; mixing npm into it adds complexity. Separate repos also allow independent versioning and CI.

### 2. Native fetch with Zero Dependencies

**Options:** (A) Native `fetch` vs. (B) `undici` or `node-fetch`
**Decision:** A -- native `fetch`
**Rationale:** Available in Node 18+ (LTS). Zero dependencies keeps the package lightweight. Allow users to pass a custom `fetch` implementation for environments that need it or for testing.

### 3. Factory Function

**Options:** (A) `createClient(opts)` factory vs. (B) `new KlartexClient(opts)` class
**Decision:** A -- factory function
**Rationale:** More idiomatic for modern TypeScript packages. Hides implementation details and allows easier future changes. The returned object is a plain interface.

### 4. ArrayBuffer Return Type for render()

**Options:** (A) `ArrayBuffer` vs. (B) `Uint8Array` vs. (C) `Buffer`
**Decision:** A -- `ArrayBuffer`
**Rationale:** Most portable across Node.js and browser/edge environments. Users can easily wrap in `Buffer.from()` for Node-specific needs or use `Uint8Array` view.

### 5. camelCase API with snake_case Mapping

**Options:** (A) Match HTTP API snake_case vs. (B) Use idiomatic camelCase
**Decision:** B -- camelCase in TypeScript, map to snake_case internally
**Rationale:** TypeScript convention is camelCase. The client handles the translation so users write `brandingDir` while the HTTP request sends `branding_dir`.

## Verification Checklist

- [ ] `render()` sends POST to `/render` with correct snake_case body and returns PDF as ArrayBuffer
- [ ] `templates()` sends GET to `/templates` and returns typed `TemplateInfo[]`
- [ ] `schema(name)` sends GET to `/templates/{name}/schema` and returns object
- [ ] HTTP errors throw `KlartexHttpError` with status, statusText, and body
- [ ] Network failures throw `KlartexError`
- [ ] `brandingDir` maps to `branding_dir` in request body
- [ ] Trailing slash in `baseUrl` is stripped
- [ ] Custom `fetch` can be injected via options
- [ ] Custom headers are merged into requests
- [ ] Package builds to both CJS and ESM
- [ ] TypeScript declarations are included in dist
- [ ] `package.json` has correct `exports`, `types`, `main`, `module` fields
- [ ] All tests pass
- [ ] No runtime dependencies (zero `dependencies` in package.json)
