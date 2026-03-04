# Rubric Mapping (Evidence Index)

## Core Pydantic Schema Design

1. Coverage (5 required concepts)
- `DocumentProfile`: [src/rataz_tech/core/models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)
- `ExtractedDocument`: [src/rataz_tech/core/models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)
- `LogicalDocumentUnit`: [src/rataz_tech/core/models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)
- `PageIndexNode` (recursive): [src/rataz_tech/core/models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)
- `ProvenanceChain`: [src/rataz_tech/core/models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)

2. Type precision
- Enums for categorical fields: origin/layout/domain/cost/chunk type in [models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)
- Structured bbox model `BBox`: [models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)

3. Provenance fields
- LDU includes `content_hash`, `page_refs`, `bounding_box`: [models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)
- `ProvenanceChain` includes `bbox` + `content_hash`: [models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)

4. Structural relationships
- LDU `parent_section` + `chunk_relationships`: [models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)
- Recursive `PageIndexNode.children`: [models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)

5. Validation
- `BBox` axis validators and `PageRef`/`PageIndexNode` range validators: [models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/models.py)
- Tests: [tests/test_schema_models.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/tests/test_schema_models.py)

## Triage Agent -- Document Classification Logic

1. Origin type detection (multi-signal)
- `char_density`, `image_ratio`, `font_metadata_present`, zero-text, mixed-mode: [src/rataz_tech/extraction/triage.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/triage.py)

2. Layout complexity detection
- Table marker + short-line ratio + line count heuristics: [triage.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/triage.py)

3. Domain hint classification (pluggable)
- Strategy interface + keyword implementation: [domain_classifier.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/domain_classifier.py)
- Config-backed keyword lists: [configs/settings.yaml](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/configs/settings.yaml)

4. Extraction cost estimation
- `DocumentProfile.extraction_cost` derivation: [triage.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/triage.py)

5. Edge case handling
- Zero-text, mixed-mode pages, form-fillable heuristics: [triage.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/triage.py)

## Multi-Strategy Extraction Implementation

1. Strategy coverage (A/B/C)
- A fast text: `FastTextExtractionStrategy`
- B layout aware: `LayoutAwareExtractionStrategy`
- C vision augmented: `VisionAugmentedExtractionStrategy`
in [src/rataz_tech/extraction/strategies.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/strategies.py)

2. Shared interface
- Common `ExtractionStrategy` protocol in [strategies.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/strategies.py)

3. Confidence scoring (A)
- Multi-signal score formula in `FastTextExtractionStrategy.extract`: [strategies.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/strategies.py)

4. Schema normalization (B)
- Normalized `ExtractedDocument` with tables/figures/bbox/page index: [strategies.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/strategies.py)

5. Budget control (C)
- Token/cost cap with hard stop + `review_required`: [strategies.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/strategies.py)
- Budget config: [settings.yaml](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/configs/settings.yaml)

6. Spatial provenance
- Page numbers + bbox in units, tables, figures, provenance chains: [strategies.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/strategies.py)

## Extraction Router with Confidence-Gated Escalation

1. Profile-based selection
- Triage decision + strategy by cost: [src/rataz_tech/extraction/factory.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/factory.py)

2. Escalation guard and multi-level path
- A→B→C retry logic and thresholds: [factory.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/factory.py)

3. Decision transparency
- Structured audit metadata: selected strategy, confidence, escalation path, review flag: [factory.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/factory.py)

4. Graceful degradation
- Final low-confidence sets `review_required`: [factory.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/factory.py)

5. Configuration
- Thresholds/rules in config, loaded via typed settings: [configs/settings.yaml](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/configs/settings.yaml), [src/rataz_tech/core/config.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/config.py)

## Externalized Configuration

1. Parameter coverage
- Confidence thresholds, escalation rules, chunk constitution, vision budget, domain keywords in [settings.yaml](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/configs/settings.yaml)

2. Integration
- Runtime config loading in [config.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/core/config.py)
- Triage/router/strategy logic consumes config values in [triage.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/triage.py), [factory.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/factory.py), [strategies.py](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/src/rataz_tech/extraction/strategies.py)

3. Onboarding readiness
- New domains can be added by editing only `extraction.domain_keywords` in [settings.yaml](/home/rata/Documents/Ephrata/work/10Acadamy/training/rataz-Wordz/configs/settings.yaml)
