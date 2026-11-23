# OrganicPath – Data Sources

**Project:** OrganicPath
**Purpose:** Help farmer groups understand organic certification requirements (NPOP and PGS-India).
**Last reviewed:** 23 November 2026

## 1. Official Data Sources

| ID | Source | URL | Format | Purpose |
|---|---|---|---|---|
| SRC-01 | APEDA NPOP Portal | https://npop.apeda.gov.in/ | Web page / PDF | Official NPOP standards and updates |
| SRC-02 | NPOP Eighth Edition 2024 | https://npop.apeda.gov.in/sites/default/files/2024-10/NPOP_Eight_Edition_2024.pdf | PDF | Organic production standards and certification requirements |
| SRC-03 | APEDA TraceNet | https://apeda.gov.in/tracenet | Web application | Traceability and certification-related information |
| SRC-04 | TraceNet Information | https://apeda.gov.in/node/81 | Web page | TraceNet modules and traceability |
| SRC-05 | PGS-India Portal | https://pgsindia-ncof.gov.in/ | Web page / PDF | Participatory Guarantee System information |
| SRC-06 | DGFT Public Notice No. 39/2024-25 | https://apeda.gov.in/sites/default/files/dgft_public_notice/PN39_English.pdf | PDF | Organic product export requirements |
| SRC-07 | Destination Country Import Rules | To be identified | Web page / PDF | Country-specific organic import requirements |

## 2. Source Format and Usage

### NPOP Standards
- Publisher: APEDA.
- Format: PDF / HTML.
- Use: Organic farming standards, conversion requirements, permitted inputs and certification requirements.
- Status: Initial source identified; latest amendments must be checked.

### PGS-India Guidelines
- Publisher: PGS-India / NCOF.
- Format: PDF / HTML.
- Use: Group certification, peer appraisal and organic farming requirements.
- Status: Latest operational manual needs to be located and verified.

### TraceNet
- Publisher: APEDA.
- Format: Web application / web pages.
- Use: Traceability and certification workflows.
- Status: Information source identified. Do not scrape login-protected information.

### Export Requirements
- Publisher: DGFT / APEDA and destination-country authorities.
- Format: PDF / HTML.
- Use: Organic product export requirements.
- Status: Destination country not yet confirmed.

## 3. Information to Extract

1. Organic crop production requirements.
2. Conversion period requirements.
3. Permitted fertilizers and soil inputs.
4. Pest and disease management.
5. Prevention of contamination.
6. Farm records and documentation.
7. Harvesting, handling and storage.
8. Certification and inspection requirements.
9. Organic product labelling.
10. Export documentation.

## 4. Initial Data Structure

| Field | Description |
|---|---|
| id | Unique record ID |
| standard | NPOP or PGS-India |
| section | Original standard section number |
| topic | Requirement topic |
| conversion_period | Required conversion period, if specified |
| permitted_input | Permitted input, if specified |
| condition | Conditions or restrictions attached to the requirement |

### Additional Metadata

- source_id
- source_title
- source_url
- source_version
- published_date
- accessed_date
- page_number
- jurisdiction
- verification_status

## 5. Data Collection Rules

- Use official government and certification sources.
- Record the source URL and original section number for every extracted requirement.
- Preserve the original meaning of each standard.
- Do not invent missing conversion periods or permitted inputs.
- Keep NPOP and PGS-India requirements separate.
- Mark unclear information for manual verification.
- Check amendments before publishing updated requirements.
- Verify requirements with an accredited certification body when necessary.

## 6. Initial Collection Checklist

- [ ] Download and inspect the latest NPOP standard.
- [ ] Identify relevant organic crop production sections.
- [ ] Locate the latest PGS-India operational manual.
- [ ] Identify conversion period requirements.
- [ ] Identify permitted input requirements.
- [ ] Record source section numbers and page numbers.
- [ ] Identify the destination country for export requirements.
- [ ] Verify the reuse terms of each source.
- [ ] Prepare structured records for database loading.

## 7. Open Questions

1. Which country will the farmer group export turmeric to?
2. Which version of the PGS-India manual should be used?
3. Which source documents permit reuse or redistribution?
4. Which requirements need verification by an accredited certification body?

**Note:** This is an initial source inventory, not a complete collection of certification rules. Verify all extracted requirements against the latest official documents before showing them to farmers.
