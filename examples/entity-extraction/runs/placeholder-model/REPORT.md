<!--
REPORT.md — placeholder for the entity-extraction example. All numbers
are illustrative (DESIGN.md §7.2); this is not a real run. Shows the
v0.10 extraction REPORT shape: per-field scores plus the extraction
failure-mode breakdown (REPORT.md.template §2.1).
-->

# spp REPORT — entity-extraction-example

**Model:** placeholder-model
**Task mode:** extraction

---

## 2. Final scores

### 2.1 Per-field scores

#### Field `entities`
Primary metric: span_f1 (IoU ≥ 0.5, type-aware)

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.88 | 60 |
| Dev (final iter) | 0.90 | 60 |
| Train (final iter) | 0.93 | 120 |

Failure-mode breakdown (test, aggregate counts only — no row content):

```
missed     : 5    (gold mention absent from prediction)
spurious   : 3    (predicted mention with no gold match)
mistyped   : 2    (right span, wrong type)
boundary   : 4    (right entity, IoU below threshold)
```

Per-type F1 (test): product 0.89, org 0.86.

#### Field `topics`
Primary metric: extraction_f1 (text alignment)

| Partition | Value | N rows |
|---|---|---|
| Test (sacred) | 0.91 | 60 |
| Dev (final iter) | 0.92 | 60 |
| Train (final iter) | 0.94 | 120 |

Failure-mode breakdown (test, aggregate counts only):

```
missed     : 6    (gold topic absent from prediction)
spurious   : 4    (predicted topic with no gold match)
```

### 2.2 Aggregate scores

| Partition | Aggregate metric | Value |
|---|---|---|
| Test (sacred) | macro | 0.895 |
| Dev (final iter) | macro | 0.91 |
| Train (final iter) | macro | 0.935 |

### 2.3 Floor compliance (per-field)

| Field | Floor | Test value | Status |
|---|---|---|---|
| entities | 0.80 | 0.88 | met |
| topics | — | 0.91 | not_specified |

---

## 5. Methodology guarantees

Per-stage information-isolation invariants: preserved. Extraction mode
changed the content shape of the discrepancy and auditor stages, not
their allow-list membership (DESIGN.md §7.1.11); the auditor remained
score-blind and the test set was read exactly once at finalization.

## RECOMMENDATION

ship — both fields clear their targets, the entities floor is met, and
the test/dev gap is within the overfitting guard band. (Placeholder
recommendation; not a real run.)
