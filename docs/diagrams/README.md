# Architecture diagrams

[`workspace.dsl`](workspace.dsl) is the editable Structurizr model for the app's
logical C4 system context and container views. It deliberately contains no live
server addresses, operator accounts or deployment paths.

The checked-in `.mmd` files are Structurizr exports. The SVGs are rendered from
those exports so readers can see the diagrams without running a tool. The process
flows embedded in the guides use Mermaid directly.

## Regenerate

Run from the repository root with Docker available. These commands work in
PowerShell and POSIX shells; `${PWD}` resolves the current directory in both.
The pinned image is Structurizr 2026.06.28.

```text
docker run --rm --network none -v "${PWD}/docs/diagrams:/workspace" structurizr/structurizr@sha256:251905a1a2d73195e84b784966babc71b329223fdbb25368261a9e3ba39041c4 validate -workspace /workspace/workspace.dsl
docker run --rm --network none -v "${PWD}/docs/diagrams:/workspace" structurizr/structurizr@sha256:251905a1a2d73195e84b784966babc71b329223fdbb25368261a9e3ba39041c4 export -workspace /workspace/workspace.dsl -format mermaid -output /workspace
npx --yes --package @mermaid-js/mermaid-cli@11.17.0 mmdc -i docs/diagrams/structurizr-system-context.mmd -o docs/diagrams/system-context.svg -c docs/diagrams/mermaid-config.json -b white
npx --yes --package @mermaid-js/mermaid-cli@11.17.0 mmdc -i docs/diagrams/structurizr-containers.mmd -o docs/diagrams/containers.svg -c docs/diagrams/mermaid-config.json -b white
```

The renderer needs Node.js and its browser dependencies. It is documentation
tooling, not an application dependency. Inspect both diagrams after generation:
valid syntax alone does not catch overlapping labels or unreadable text.

References: [Structurizr DSL](https://docs.structurizr.com/dsl),
[Structurizr export](https://docs.structurizr.com/commands/export),
[Mermaid CLI](https://github.com/mermaid-js/mermaid-cli).
