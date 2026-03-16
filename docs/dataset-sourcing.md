# Dataset Sourcing Brief

This project needs real public data for:

1. spending and cashflow structure
2. financial stress and hardship labels
3. financial well-being targets
4. student-finance context

## Sourcing conclusion

There does not appear to be a fully open, official, transaction-level public dataset that is both:

- explicitly college-student-only
- longitudinal at the individual level
- downloadable without restricted-access licensing

That means the strongest honest approach is:

- train the core spending model on public consumer expenditure microdata
- learn hardship and financial-fragility targets from public finance surveys
- treat "student" as a filtered subgroup when the source supports age, education, or student-finance variables
- use student-specific education-finance datasets for benchmarking and framing, not as the main sequence-training source

This is an inference based on the official sources reviewed below.

## Recommended dataset stack

### Tier 1: primary training source

#### 1. BLS Consumer Expenditure Surveys Public Use Microdata

- Source: U.S. Bureau of Labor Statistics
- URL: <https://www.bls.gov/cex/pumd.htm>
- Why it matters:
  - this is the best official public source for real expenditure microdata
  - it includes expenditures, income, and demographics
  - data are published in Interview and Diary files
  - files are available in SAS, Stata, and comma-delimited formats
- Best use in this project:
  - expense-category modeling
  - spending sequence construction
  - burn-rate and balance-proxy feature engineering
  - category normalization for food, transport, entertainment, shopping, and essentials
- Limitations:
  - not student-only
  - public data is anonymized and not a direct bank-transaction feed
  - "student finance" has to be approximated through age and related demographic filters where supported

### Tier 1: primary label source

#### 2. CFPB Making Ends Meet Public Use File

- Source: Consumer Financial Protection Bureau
- URL: <https://www.consumerfinance.gov/data-research/making-ends-meet-survey-data/public-data/>
- User guide: <https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_public-use-file_user-guide.pdf>
- Why it matters:
  - official public-use financial-stress survey data
  - includes financial well-being, bill difficulty, and ability to cover expenses after income loss
  - includes 2019 plus all samples from 2022 forward
  - public use files include survey variables and, for early waves, select derived credit variables
  - later releases operate as yearly rolling panels
- Best use in this project:
  - define risk and hardship labels
  - train or calibrate financial-crisis outputs
  - create evaluation targets beyond simple spending prediction
  - model response variables such as difficulty paying bills and expense coverage resilience
- Limitations:
  - survey-based rather than transaction-level
  - later samples do not include the same credit variables as the earliest public release
  - usage is subject to CFPB acceptable-use terms

### Tier 1: secondary hardship and student-debt source

#### 3. Federal Reserve SHED

- Source: Board of Governors of the Federal Reserve System
- URL: <https://www.federalreserve.gov/consumerscommunities/shed_data.htm>
- Why it matters:
  - annual public-use CSV files are available from 2013 through 2024
  - includes financial fragility, emergency savings, banking, credit access, education, and student-loan modules
  - some years include identifiers for limited cross-year linkage in the public files
- Best use in this project:
  - benchmark financial-risk predictions
  - auxiliary labels for hardship, savings resilience, and financial well-being
  - student-loan and education-related subgroup analysis
- Limitations:
  - annual survey, not transaction history
  - not a dedicated student dataset

### Tier 2: validated well-being calibration source

#### 4. CFPB National Financial Well-Being Survey

- Source: Consumer Financial Protection Bureau
- URL: <https://www.consumerfinance.gov/data-research/financial-well-being-survey-data/>
- Why it matters:
  - official public CSV
  - includes the CFPB 10-item financial well-being scale and related covariates
  - includes income, employment, savings, safety nets, financial behaviors, skills, and attitudes
- Best use in this project:
  - validate or calibrate a financial well-being head or score
  - support explainability and target definition
  - provide a cleaner well-being target than ad hoc proxy labels
- Limitations:
  - cross-sectional
  - not expense-sequence data

### Tier 3: student-finance benchmark source

#### 5. NCES National Postsecondary Student Aid Study

- Source: National Center for Education Statistics
- URL: <https://nces.ed.gov/surveys/npsas/availabledata.asp>
- Why it matters:
  - the strongest official student-finance dataset for higher-education financing context
  - focuses on how students finance postsecondary education
  - contains student demographic, enrollment, and financial-aid variables
- Best use in this project:
  - benchmark claims about student financial context
  - define subgroup assumptions and report context
  - support the academic framing of the project
- Limitations:
  - public access is through NCES DataLab rather than simple bulk CSV download
  - not suitable as the main ingestion source for the live training pipeline
  - not transaction-level spending data

## Datasets not chosen as phase-1 core

### ECB Consumer Expectations Survey

- Source: European Central Bank
- URL: <https://www.ecb.europa.eu/stats/ecb_surveys/consumer_exp_survey/html/data_methodological.en.html>
- Why it is interesting:
  - official individual-level background, monthly, and quarterly microdata
  - published quarterly
  - useful for panel and expectation modeling
- Why it is not phase 1:
  - cross-region integration adds currency, policy, and comparability complexity
  - the U.S.-focused stack above is cleaner for the first real training pipeline

## Recommended acquisition order

1. CFPB Making Ends Meet
2. Federal Reserve SHED
3. CFPB Financial Well-Being Survey
4. BLS Consumer Expenditure Survey PUMD
5. NCES NPSAS for benchmark analysis only

This order is intentional:

- the first three sources are easier to use for label engineering and benchmarking
- BLS CE is the main expenditure engine and should be mapped carefully into the project schema
- NPSAS helps the student framing, but it should not block model development

## How these datasets map into the project

### Task A: spending representation and forecasting

- Primary source: BLS CE PUMD
- Output candidates:
  - next-period spending
  - category spend mix
  - high-burn periods

### Task B: financial-risk and hardship modeling

- Primary sources:
  - CFPB Making Ends Meet
  - SHED
- Output candidates:
  - difficulty paying bills
  - low expense-cover capacity
  - fragile financial state

### Task C: well-being calibration

- Primary source:
  - CFPB Financial Well-Being Survey
- Output candidates:
  - well-being score or band

### Task D: student-context benchmarking

- Primary source:
  - NPSAS
- Output candidates:
  - reporting context only
  - subgroup assumptions and justification

## Honest project positioning

The final project should not claim:

- "trained only on college students" unless we later collect real student-specific logs
- "bank transaction modeling" if the model is trained mostly on survey or expenditure microdata

The final project can honestly claim:

- real neural-network training on official public finance datasets
- real financial-risk evaluation using public microdata and survey labels
- student-oriented adaptation through subgrouping, label design, and interface goals

## Next implementation step

Build ingestion in this order:

1. SHED downloader and schema mapper
2. CFPB MEM downloader and schema mapper
3. CFPB Financial Well-Being downloader and calibration mapper
4. BLS CE ingestion and category harmonization
5. unified training tables for:
   - expenditure sequences
   - hardship labels
   - well-being labels
