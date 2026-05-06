# Excerpt: plan.md §2 (Class definition)

**Label space:** {Bug, Feature, Question, Other}

**Class definitions:**

- **Bug:** A reported defect — observed behavior that contradicts
  documented or intended behavior **of this library**. Positive
  shape: "Calling `compute()` with an empty list raises a
  TypeError instead of returning [] like the docs say." Defects
  in dependencies, infrastructure, or downstream services are
  not Bugs against this library; they are Other.
- **Feature:** A request for new capability or extension. Positive
  shape: "Add a JSON output mode to the CLI."
- **Question:** A request for clarification or help understanding
  existing behavior, where the user has not asserted a defect.
  Positive shape: "Does `compute()` handle Unicode keys?"
- **Other:** Documentation issues, build/CI breakage reports,
  repo hygiene, or any issue that does not fit the first three.
  **Includes infrastructure breakage where the library itself is
  not the failing component** (CI environment problems, internal
  service outages, etc.). Positive shape: "Typo in README"; "CI
  build failing because the docker image cannot be pulled."

**Known borderline cases:**

- Question vs Bug: when the user describes surprising behavior
  without explicitly asserting it is a defect.
