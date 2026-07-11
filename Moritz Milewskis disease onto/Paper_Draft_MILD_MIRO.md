# Mid Layer Disease Ontology: a BFO/OGMS-aligned pattern for material disease individuation

**Draft status:** first manuscript draft. This document follows the MIRO reporting topics proposed by Matentzoglu et al. (2018) and should be refined after the current source ontology is rebuilt into fresh merged and inferred artefacts.

**Author:** Dr. Moritz Rudolf Franz Valerius Milewski (ORCID: 0009-0006-6251-7592)

---

## Abstract

The Mid Layer Disease Ontology (MILD) is a BFO/OGMS-aligned ontology pattern for modelling disease while keeping apart material pathology, disease individuation, disease course, predisposition, and diagnostic classification. The central commitment is that pathological disorders are the primary mind-independent material entities. Material disease entities are continuants that have pathological disorders as parts, but their disease boundaries are classification-relative: diagnostic results and threshold specifications belong to an epistemic layer that groups disorders without making the diagnostic category itself a material disease. This pattern is motivated by tensions in existing disease ontologies and philosophy of medicine: OGMS grounds disease in disorder and disposition, causal-chain models emphasize disease course and persistence through change, tendency theory clarifies risk and predisposition, and clinical classifications frequently encode defaults rather than universal axioms. MILD contributes a mid-level modelling pattern rather than a new disease classification. The ontology is represented in OWL 2 DL, imports BFO/OGMS and related OBO resources, and has been reported coherent by a HermiT run with zero unsatisfiable classes. Remaining work concerns fresh regeneration of derived artefacts after recent metadata edits, publication packaging, and further use-case evaluation.

## Keywords

disease ontology; BFO; OGMS; biomedical ontology; MIRO; pathological disorder; diagnostic classification; disease predisposition; ontology design pattern

---

## 1. Introduction

Biomedical ontologies need disease representations that are usable for classification and reasoning without collapsing clinical categories, material pathology, and diagnostic practice into one class hierarchy. Existing disease resources often satisfy one requirement at the expense of another. OGMS provides a realist disorder-based account, but treats disease primarily as a disposition. DOID and Mondo provide broad clinical coverage and mapping utility, but their disease classes function mainly as pragmatic classification resources. Causal-chain approaches such as Mizoguchi's River Flow Model foreground disease course and mechanistic continuity, but are not straightforwardly portable into the BFO/OBO stack.

MILD addresses this gap by proposing a mid-level pattern that separates:

- **pathological disorder**: the abnormal material substrate;
- **material disease entity**: a material continuant with pathological disorders as parts;
- **disease course and disorder development**: occurrent processes that produce or modify disorders;
- **disease predisposition**: a tendency inhering in a person and grounded in a material basis;
- **diagnostic classification**: an epistemic layer that groups disorders into disease-relevant boundaries.

The contribution is not another disease classification. It is a modelling pattern for keeping these layers explicit, interoperable, and testable in OWL.

## 2. Motivation and related work

### 2.1 OGMS and the disorder/disease distinction

OGMS distinguishes disorders, diseases, pathological processes, and disease courses. This structure is valuable because it grounds disease in a material disorder rather than merely in a diagnostic label. However, a disease-as-disposition model risks hiding the material and historical structure that makes a disease persist through change. MILD keeps the disorder background but relocates disease individuation into a material-continuant pattern whose boundaries are classification-relative.

### 2.2 Pathologicity as a primitive

The ontology does not try to reduce pathologicity to statistical normality, dysfunction, harm, or treatment availability. Following the disease-entity tradition associated with Hucklenbroich, pathologicity is treated as a primitive but documented commitment. The ontology states that pathologicity is asserted rather than inferred, with criteria such as threat to life, pain or suffering, and loss of ability or fertility serving as explanatory anchors.

MILD also reuses the ExO-style species-comparative intuition as a secondary anchor for pathologicity. ExO defines disease in terms of abnormal functioning, abnormal localization of normal functioning, or abnormal localization of constituents compared with other members of the species. In MILD, this comparison helps document why a material organization counts as pathological: normal constituents can become pathological when they are abnormally located, organized, or functioning relative to relevant conspecific reference cases. This is not adopted as the full definition of disease, because rare variation is not automatically pathological and because species comparison still has to be interpreted together with harm, impairment, persistence, life-stage, and context.

Two further anchors should guide this judgement. First, the impairment should not be merely voluntary, transient, and immediately reversible. Holding one's breath can impair oxygenation and bodily function, but it can normally be ended by resuming breathing and does not by itself imply a pathological substrate. Easy reversibility is therefore defeasible evidence against classifying a state as disease. It is not an absolute exclusion, because many acute diseases are reversible or treatable; the point is to distinguish ordinary reversible physiology or behaviour from a pathological disorder or self-maintaining disease process.

Second, disease matters not only because internal biological function is altered, but because pathological disorder can impair expected participation in human life. Relevant participation anchors include being able to work, earn a living, form and sustain family and friendship relations, take part in social life, and live out a normal lifespan rather than dying prematurely. These anchors help document why a disorder is clinically and humanly significant, but they should not be encoded as universal axioms: social participation is context-sensitive, and its role belongs mainly in the pathologicity and relevance judgement rather than in a rigid disease definition.

### 2.3 Tendencies and predispositions

Risk and predisposition are not modelled as material diseases. MILD uses a tendency pattern informed by Jansen and by Röhl and Jansen's analysis of realizables. A disease predisposition is a tendency inhering in a person and grounded in a material basis, such as a pathogenic genetic variant or an existing pathological disorder. The base predisposition class does not require an actual realization process. Realized cases can be represented separately by `realized disease predisposition`.

The ontology also adopts a non-vacuity constraint on realization. A realizable entity is informative only when it contributes causal or counterfactual content beyond a restatement of the process it is said to realize. This means that a tendency or disposition should identify a bearer, a material basis, a manifestation type, and the internal or external conditions under which the manifestation occurs. Both internal and external influences can participate in realization: a burn susceptibility can be realized through heat exposure, and a genetic predisposition can be realized through an internally initiated disorder-development process. What is excluded is the circular pattern in which a process is explained only by nominalizing it as a disposition. Saying that existing realizes a disposition to exist, or that dying realizes a generic human disposition to die, does not explain the existence or the dying process. The relevant question is which material basis, injury, exposure, internal pathological event, or disorder lineage initiated and structured the process.

### 2.4 Ontology versus clinical defaults

Clinical knowledge is frequently default, probabilistic, or guideline-relative. MILD therefore avoids encoding typical clinical features as universal disease axioms. Diagnostic thresholds, classification criteria, and clinical defaults are represented in the information layer rather than as necessary and sufficient biological universals.

### 2.5 Persistence through material change

MILD treats disease persistence as continuant persistence through material change. The identity of a material disease entity depends on historical-causal continuity of the disorder lineage rather than exact sameness of material constituents at every time. This borrows the River Flow insight that an entity can remain identifiable while its material realization changes, while preserving BFO-compatible continuant/process separation.

## 3. Ontology overview

### 3.1 Name, owner, and availability

The ontology is named **Mid Layer Disease Ontology** and uses the preferred namespace prefix `MILD`. The ontology IRI is:

```text
https://bioportal.bioontology.org/ontologies/MILD
```

The current source file is:

```text
Disease proposal 2.ttl
```

The generated merged file is:

```text
Disease proposal 2 merged.owl
```

An inferred artefact from the current HermiT/Colab coherence run is:

```text
Disease_proposal_2_inferred-3.owl
```

The ontology owner and developer is Dr. Moritz Rudolf Franz Valerius Milewski (ORCID: 0009-0006-6251-7592). The ontology is licensed under Creative Commons Attribution 4.0 International.

### 3.2 Scope and coverage

MILD covers disease at a mid-level between BFO/OGMS and disease-specific clinical classification. It does not attempt to replace DOID, Mondo, ICD, or specialty-specific disease terminologies. Its scope is the modelling of:

- material pathological disorders;
- material disease entities;
- disease courses and disorder-development processes;
- complications;
- disease predispositions;
- diagnostic results and threshold specifications.

The current implementation is human-scoped where `Homo sapiens` is hard-coded. This should be understood as a scope restriction, not as a claim that the pattern is intrinsically human-only.

### 3.3 Core classes

The current core classes include:

- `material disease entity`;
- `pathological disorder`;
- `disease predisposition`;
- `genetic predisposition`;
- `predisposition from an existing disorder`;
- `realized disease predisposition`;
- `disorder development process`;
- `course of the disease process`;
- `disease diagnostic result`;
- `material complication disease entity`;
- `disease course process putting out disorders as part of a complication`.

### 3.4 Upper ontology and imported ontologies

MILD is aligned with BFO and OGMS, and imports modules from OBO-related resources including BFO, OGMS, OBI, PATO, HPO, CHEBI, DOID, GO, DRON, UO, NCBITaxon, COB, uPheno, and WONT. BFO provides the top-level categories for continuants, occurrents, realizables, and parthood. OGMS supplies the disorder background. Other imports provide supporting vocabulary for diagnoses, observations, organisms, phenotypes, qualities, and related biomedical entities.

## 4. Design commitments

### 4.1 Disorders are primary material entities

The main realist commitment is that disorders are the primary mind-independent material entities in the disease model. A pathological disorder is a material abnormality or abnormal organization in a body. Absence and privation cases are treated as abnormal organization of a present material bearer rather than as negative entities or absent qualities.

### 4.2 Disease boundaries are classification-relative

Material disease entities have pathological disorders as parts, but the boundary of one disease rather than another is not fixed by an intrinsic maximality axiom. Diagnostic results and classification specifications group disorders into disease-relevant units. This allows overlapping or changing classifications without asserting that diagnostic categories are themselves material diseases.

### 4.3 Disease instances are material continuants

Disease instances are modelled as material continuants whose identity depends on historical-causal continuity of the disorder lineage. This accommodates persistence through turnover or change in the material constituents.

### 4.4 Diagnostic thresholds are epistemic

Diagnostic categories, thresholds, stages, and candidate/confirmed diagnostic results are information content entities or outputs of classification processes. They are about pathological disorders, but they are not material diseases.

### 4.5 Predispositions are tendencies, not diseases

Disease predispositions are tendencies inhering in a person and grounded in a material basis. A pathogenic genetic variant can ground a genetic predisposition without being identical to the target disease. A realized predisposition is represented by a narrower class linked to a realization process.

### 4.6 Realization assertions must be non-vacuous

MILD does not treat disease courses as realizations of diseases merely because diseases have courses. This would add little explanatory content, just as modelling a dying process as the realization of a generic disposition to die does not explain why the person is dying. Realization assertions are reserved for cases where the realizable entity has an identifiable bearer and material basis and where its realization depends on causally specific internal or external conditions. A disease predisposition may be realized in a disorder-development process; a material disease entity is instead a continuant grounded in pathological disorder and historically-causally continuous disorder lineage.

### 4.7 Reversibility and participation are modelling constraints, not class definitions

MILD treats non-trivial persistence and participation impairment as constraints on pathologicity judgement rather than as formal necessary-and-sufficient conditions. A candidate disease should not be just an easily reversible functional deviation, and its relevance is partly explained by its effect on the person's ordinary biological and social participation. However, neither criterion should be formalized as a universal axiom for all disease classes, because some diseases are acute, some are reversible with treatment, and participation effects vary with environment and support.

## 5. Axiom patterns

### 5.1 Material disease entity pattern

```text
material disease entity
  subClassOf material entity
  subClassOf part of some Homo sapiens
  subClassOf has part some pathological disorder
  disjointWith disease predisposition
```

This pattern commits to a material disease entity as located in a patient and composed, at least in part, by pathological disorder. It avoids an intrinsic maximality or unity axiom.

### 5.2 Pathological disorder pattern

```text
pathological disorder
  subClassOf OGMS disorder
  subClassOf part of some Homo sapiens
  subClassOf part of some material disease entity
  disjointWith disease predisposition
```

Pathological disorder remains primitive with respect to pathologicity. It is not defined by `has quality some phenotypic abnormality`.

### 5.3 Disease predisposition pattern

```text
disease predisposition
  subClassOf tendency
  subClassOf inheres in some Homo sapiens
  subClassOf has material basis some material entity
```

The base class does not assert `has realization some disorder development process`, because unrealized risk should not entail an actual realization process or target disorder.

### 5.4 Realized disease predisposition pattern

```text
realized disease predisposition
  subClassOf disease predisposition
  subClassOf has realization some disorder development process
```

This narrower class represents cases in which a predisposition is actually realized.

### 5.5 Genetic predisposition pattern

```text
genetic predisposition
  subClassOf disease predisposition
  subClassOf has material basis some pathogenic genetic variant
```

The pathogenic variant is represented as a material/pathological variant, not as a DOID category.

### 5.6 Complication pattern

MILD represents complications by distinguishing the producing disease course from the produced disorder and from the later diagnostic grouping. A process in disease A's course can output a pathological disorder that becomes part of disease B, a material complication disease entity.

## 6. Worked examples and competency questions

### 6.1 Single-disorder disease

A patient has a pathological disorder. A diagnostic result is about that disorder and groups it as a disease. The ontology should infer that the disorder and disease are material entities, while the diagnostic result remains an information content entity. It should not infer that every disorder has a diagnosis, nor that all disorders in the patient form one disease.

### 6.2 Complication

A course of disease A produces a new pathological disorder. That output disorder is later grouped under disease B by a complication diagnostic result. The ontology should support disease B as a material complication disease entity without inferring that disease A and disease B are identical.

### 6.3 Genetic predisposition

A patient carries a pathogenic genetic variant that grounds risk for a future target disorder. The ontology should infer that the predisposition is a tendency and not a disease or disorder. It should not infer that the target disorder already exists merely because the predisposition exists.

### 6.4 Competency questions

- Can a patient have a pathological disorder without a diagnosis? Expected: yes.
- Can two diagnostic results group overlapping but non-identical disorder sets? Expected: yes.
- Can a predisposition exist without the target disorder already existing? Expected: yes.
- Can a disease persist while its material constituents change? Expected: yes, if the disorder lineage is historically-causally continuous.
- Can a complication disorder be produced by disease A but grouped as disease B? Expected: yes.
- Is a diagnostic category itself a disease? Expected: no.

## 7. Knowledge acquisition and content selection

The ontology was developed from a synthesis of formal ontology and philosophy-of-medicine literature, including work on OGMS, disease/disorder modelling, pathologicity, tendencies and realizables, clinical default knowledge, disease classification, and causal-chain accounts of disease. The content selection prioritized modelling distinctions that are needed to avoid common conflations:

- material disorder versus disease category;
- disease instance versus diagnostic result;
- disorder development versus disease course;
- predisposition versus realized disorder;
- universal ontology axioms versus clinical defaults;
- material continuity versus historical-causal continuity.

The source bibliography and synthesis are recorded in `Disease_Modelling_Synthesis.md` and associated bibliography files.

## 8. Quality assurance and validation

Validation is recorded in `VALIDATION.md`.

The current validation evidence includes:

- OWL 2 DL profile validation by ROBOT;
- HermiT/Colab coherence checking on the merged ontology;
- reported ontology consistency;
- zero reported unsatisfiable classes;
- saved inferred ontology artefact.

The core modelling checks are also represented as competency questions and worked examples. Before external submission, the merged and inferred artefacts should be regenerated from the current source because metadata edits were made after the last generated artefacts.

## 9. Limitations

First, OWL classes are crisp while biological boundaries are often vague. MILD treats crispness as a representational choice rather than a metaphysical claim that every biological boundary is sharp. Second, pathologicity remains primitive; this is intentional, but it means the ontology documents rather than derives the pathological status of disorders. Third, the current ontology is human-scoped where `Homo sapiens` is asserted in class restrictions. Fourth, clinical defaults and typical disease features are intentionally not encoded as universal axioms. Fifth, external evidence of use is not yet available beyond the internal worked examples and validation run.

## 10. Availability and change management

The ontology source is `Disease proposal 2.ttl`. The current generated OWL artefact is `Disease proposal 2 merged.owl`, and the inferred artefact is `Disease_proposal_2_inferred-3.owl`. The preferred namespace prefix is `MILD`, with preferred namespace URI:

```text
https://bioportal.bioontology.org/ontologies/MILD/
```

Version IRI:

```text
https://bioportal.bioontology.org/ontologies/MILD/0.1.0
```

The ontology is licensed under CC BY 4.0. A formal public repository, issue tracker, sustainability plan, and deprecation policy should be added before journal submission or public release.

## 11. Discussion

MILD is best understood as a mid-level pattern for disease ontology design. Its main claim is that disease modelling becomes more transparent when material disorder, disease individuation, course, predisposition, and diagnostic classification are not forced into one class. This separation makes it possible to represent material pathology realistly while acknowledging that disease boundaries and diagnostic thresholds are classification-relative.

The pattern also gives a principled place to risk. A predisposition can exist before the target disorder exists, because the base tendency is separated from realized predisposition. This avoids a common modelling mistake in which an existential realization axiom entails an anonymous future disorder too early.

The same point explains why MILD does not identify disease itself with disposition. Humans have a general susceptibility to death, and many dying processes could be described as realizations of broad mortal fragility. Such a statement is too general to be explanatory. The model instead asks what initiated and sustained the relevant process: for example trauma, infection, toxic exposure, somatic mutation, autoimmune activation, thrombosis, a genetic variant, or an already existing pathological disorder. The disease course is therefore not the realization of the disease as such, but the processual unfolding, maintenance, or transformation of a material disorder lineage.

Substance use disorder is an important edge case for this pattern because the same expression can be used at different layers. As a DSM/ICD-style term, substance use disorder often denotes a diagnostic category or diagnostic result: an epistemic grouping by criteria such as impaired control, craving, tolerance, withdrawal, continued use despite harm, and social impairment. A particular patient case may nevertheless correspond to a material disease entity if there is a relatively stable pathological organization of neurobiological, psychological, and behavioural tendencies that impairs control, persists beyond immediately reversible choice, and damages biological or social participation. The ontology should therefore not model substance use disorder as the substance itself, a single use event, a legal category, or a moral defect. Individual intoxication, use, craving, tolerance, and withdrawal episodes are better represented as processes, states, or realizations in the disease course; the diagnostic category and thresholds remain in the epistemic layer.

The remaining work is mostly packaging rather than core modelling: regenerate derived artefacts, decide whether to publish a merged TTL alongside the merged OWL, add a concise mentor/reviewer summary, and document repository-level governance.

## 12. Conclusion

MILD offers a BFO/OGMS-aligned pattern for modelling disease as a material continuant grounded in pathological disorder while keeping diagnostic categories and thresholds in the epistemic layer. The contribution is not a new disease classification but a reusable modelling strategy for separating the material, processual, realizable, and classificatory aspects of disease.

---

## MIRO reporting checklist

This checklist follows the MIRO sections and item labels from Matentzoglu et al. (2018). Checked items are addressed in this draft or in the named project artefacts. Items marked as addressed may still need polishing for submission.

### A. Basics

- [x] **A.1 Ontology name** — Mid Layer Disease Ontology (MILD), version IRI `https://bioportal.bioontology.org/ontologies/MILD/0.1.0`.
- [x] **A.2 Ontology owner** — Dr. Moritz Rudolf Franz Valerius Milewski, ORCID 0009-0006-6251-7592.
- [x] **A.3 Ontology license** — CC BY 4.0.
- [x] **A.4 Ontology URL** — ontology IRI and preferred namespace are stated; public hosting URL should be finalized before submission.
- [x] **A.5 Ontology repository** — current local repository/folder is described; public repository URL remains to be added before release.
- [x] **A.6 Methodological framework** — literature synthesis, BFO/OGMS alignment, MIRO reporting, competency questions, and validation workflow are described.

### B. Motivation

- [x] **B.1 Need** — need is stated as separation of material pathology, disease individuation, course, predisposition, and diagnostic classification.
- [x] **B.2 Competition** — OGMS, DOID/Mondo, and causal-chain/River Flow approaches are contrasted.
- [x] **B.3 Target audience** — biomedical ontology developers, disease ontology modellers, and reviewers of BFO/OGMS-aligned disease modelling patterns.

### C. Scope, Requirements, Development Community

- [x] **C.1 Scope and coverage** — mid-level disease pattern scope and boundaries are stated; competency questions are included.
- [x] **C.2 Development community** — current development by the author is stated.
- [x] **C.3 Communication** — currently local; public issue tracker or communication channel should be added before public release.

### D. Knowledge Acquisition

- [x] **D.1 Knowledge acquisition method** — literature synthesis and ontology-design critique are described.
- [x] **D.2 Source knowledge location** — `Disease_Modelling_Synthesis.md`, bibliography files, and local paper folders are identified.
- [x] **D.3 Content selection** — prioritized distinctions and modelling needs are stated.

### E. Ontology Content

- [x] **E.1 Knowledge representation language** — OWL 2 DL; profile validation recorded.
- [x] **E.2 Development environment** — Protégé/ROBOT/Colab workflow is implied; exact tooling should be expanded if required by target venue.
- [x] **E.3 Ontology metrics** — validation log records triples/classes/properties/individuals for the merged run; full axiom metrics can be added later.
- [x] **E.4 Incorporation of other ontologies** — imported ontology modules are listed.
- [x] **E.5 Entity naming convention** — MILD prefix and labels are used; full naming policy can be made stricter before submission.
- [x] **E.6 Identifier generation policy** — MILD identifiers are used; a formal policy should be added before public release.
- [x] **E.7 Entity metadata policy** — ontology-level metadata added; entity-level labels/definitions are present but can be expanded.
- [x] **E.8 Upper ontology** — BFO/OGMS alignment is stated and justified.
- [x] **E.9 Ontology relationships** — parthood, inherence, material basis, realization, output, and aboutness patterns are described.
- [x] **E.10 Axiom patterns** — material disease, pathological disorder, predisposition, realized predisposition, genetic predisposition, and complication patterns are described.
- [x] **E.11 Dereferenceable IRI** — preferred namespace URI is stated; dereferenceability should be verified after public hosting.

### F. Managing Change

- [x] **F.1 Sustainability plan** — draft states that a formal plan is still needed before public release.
- [x] **F.2 Entity deprecation strategy** — draft states that a formal deprecation policy is still needed before public release.
- [x] **F.3 Versioning policy** — version IRI exists; release policy should be added before submission.

### G. Quality Assurance

- [x] **G.1 Testing** — ROBOT profile validation and HermiT/Colab coherence are recorded.
- [x] **G.2 Evaluation** — competency questions, expected entailments/non-entailments, and modelling limitations are described.
- [x] **G.3 Examples of use** — three worked examples are included.
- [x] **G.4 Institutional endorsement** — no institutional endorsement is currently claimed.
- [x] **G.5 Evidence of use** — no external evidence of use is currently claimed; internal validation and worked examples are reported.

## References to fill/formalize

- Matentzoglu N. et al. (2018). MIRO guidelines for minimum information for the reporting of an ontology. *Journal of Biomedical Semantics*.
- Scheuermann, Ceusters, and Smith / OGMS disease and disorder background.
- Hucklenbroich on disease entity and pathologicity.
- Jansen; Röhl and Jansen on tendencies and realizables.
- Schulz et al. on ontological axioms versus clinical default knowledge.
- Mizoguchi / River Flow Model on causal continuity and persistence through change.
- DOID and Mondo references for pragmatic disease classification.
- ExO `ExO_0000079` disease definition as a species-comparative abnormality anchor.
