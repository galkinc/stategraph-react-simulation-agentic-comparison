# Scenario Data Provenance

## Source corpus

The 45 dialogue scenarios are derived from **MTS-Dialog** — a public corpus of doctor–patient dialogues created with clinician annotators, released under the **CC BY 4.0** license:

- Dataset: https://github.com/abachaa/MTS-Dialog (CC BY 4.0, see `LICENSE.txt` in the dataset repository)
- Paper: Asma Ben Abacha, Wen-wai Yim, Yujian Fan, Thomas Lin. *An Empirical Study of Clinical Note Generation from Doctor-Patient Encounters.* EACL 2023, pages 2291–2302 — https://aclanthology.org/2023.eacl-main.168

The exact source file used for this study is `Correlation-Study/MTS-Dialog-Automatic-Summaries-ValidationSet.csv` from the MTS-Dialog repository (the 100-dialogue validation split with reference and automatic summaries attached). The same validation dialogues are also available as `Main-Dataset/MTS-Dialog-ValidationSet.csv`.

## Selection pipeline

1. **Scripted filter** (`src/data_process/raw_data_scripts/prepare.py`):
   - deduplicate by dialogue ID;
   - keep dialogues with **at least 3 patient turns**.

   Applied to the validation set, this filter yields **48 candidate dialogues**.

2. **Proxy-dialogue exclusion (manual):** 3 of the 48 candidates are dialogues in which the patient is substantially represented by a third party — a `Guest_family` or `Guest_clinician` speaker answers medical questions on the patient's behalf:

   - ID **39** — a friend/coworker answers for the burn patient;
   - ID **59** — a family member reports the patient's history for him;
   - ID **62** — a clinician "represents the patient's case" at the start of the encounter.

   Excluding these three yields the final **45 scenarios** used in the benchmark. Dialogues in which the patient speaks for themselves and a relative merely accompanies the conversation (e.g. IDs 17, 37) were kept.

3. **Entity extraction:** the patient turns of the 45 dialogues are processed with **AWS Comprehend Medical** (raw outputs are analyzed by `src/data_process/raw_data_scripts/check_categories.py`). The extracted entities are assembled into structured **patient profiles** (`patient_profiles.jsonl`) that drive the LLM patient simulator in both orchestration strategies.

## Reproducibility

Everything needed to regenerate the scenario set is public:

1. Download `MTS-Dialog-Automatic-Summaries-ValidationSet.csv` from the MTS-Dialog repository (CC BY 4.0).
2. Run `src/data_process/raw_data_scripts/prepare.py` — the scripted filter yields 48 candidate dialogues.
3. Exclude the three proxy dialogues (IDs 39, 59, 62) — the final 45 scenarios.
4. Run the AWS Comprehend Medical extraction over the patient turns.
5. Assemble the patient profiles and feed them into the simulator (see `src/`).

The derived artifacts (parsed dialogues, Comprehend Medical raw outputs, patient profiles) are not stored in this repository; they are available upon request.

## Attribution

If you use the scenario data or the derived patient profiles, please cite the MTS-Dialog paper above and attribute the dataset under the terms of CC BY 4.0.
