# Project Governance and Leadership

FleetMate is committed to building a transparent, community-oriented, and sustainable open-source project following the guidelines set forth in the [Open Source Guide on Leadership and Governance](https://opensource.guide/leadership-and-governance/).

---

## 🏛️ Governance Structure

FleetMate currently operates under a **Benevolent Dictator for Life (BDFL) / Lead Maintainer** governance model, supported by community contributors. As the project community grows, governance may transition to a steering committee.

### Roles and Responsibilities

#### 1. Lead Maintainer / Project Lead
- **Current Lead**: Rodolfo Concepcion ([@rodolfoconcepcion](https://github.com/rodolfoconcepcion))
- **Responsibilities**:
  - Setting overall architectural direction, protocols, and release roadmap.
  - Final decision-making authority on pull requests, breaking changes, and security patches.
  - Enforcing the [Code of Conduct](CODE_OF_CONDUCT.md).
  - Managing repository secrets, publishing PyPI packages, and container images.

#### 2. Core Contributors & Maintainers
- Contributors who have demonstrated consistent, high-quality involvement.
- **Responsibilities**:
  - Triaging issues and pull requests.
  - Code review and quality enforcement (tests, linting, typing).
  - Assisting users in GitHub Discussions.

#### 3. Community Contributors
- Anyone who submits a bug report, documentation improvement, code fix, or answers community questions.
- Contributions are welcome from all individuals who adhere to our Code of Conduct.

---

## 🗳️ Decision-Making Process

1. **Rough Consensus**: Maintainers and contributors discuss non-trivial architectural changes in GitHub Issues or Discussions. Most decisions are resolved by friendly consensus.
2. **Breaking Changes**: Proposals altering database schemas, telemetry field specifications, or mTLS certificate handshakes require documented discussion and approval from the Lead Maintainer.
3. **Automated Releases**: FleetMate uses [Release Please](https://github.com/googleapis/release-please) and Conventional Commits for deterministic, semantic versioning.

---

## 🔑 Commit and Merge Access

- Pull requests require passing CI checks (Lint, Type Check & Test, CodeQL, Secret Scanners).
- Commits are squashed or merged according to Conventional Commits standards.
- Commit access is granted by the Lead Maintainer to contributors who display deep technical reliability, good judgment, and constructive community engagement over time.
