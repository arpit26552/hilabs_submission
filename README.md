# Provider Data Analytics Platform
# Repository Link
## https://github.com/VKprogrammer/HiLabs_Submission
# video demo link 
## https://drive.google.com/file/d/1UzAspErPr49aTHgvIZB5uTWsXJPHL2y4/view?usp=sharing
# Installation & Setup
## Prerequisites

Python 3.11 (recommended for optimal compatibility)
Git for cloning the repository

Quick Start Guide

#### 1) Clone Repository
git clone (https://github.com/VKprogrammer/HiLabs_Submission)

#### 2) Create Virtual Environment
 py -3.11 -m venv .venv
.venv\Scripts\Activate
Note: On Linux/macOS, use:
python3.11 -m venv .venv
source .venv/bin/activate

#### 3) Install Dependencies
pip install -r requirements.txt

#### 4) Run Platform
python run.py
The system will automatically:

Process the provider data
Generate validation reports
Create the database
Launch the Streamlit dashboard

Allow Streamlit permissions when prompted, and your browser will open the platform interface.

### What's Included
The repository contains all necessary files:

Provider roster data (provider_roster_with_errors.csv)
Ground truth databases (NY and CA medical license databases)
Mock NPI registry for validation
All processing scripts and dependencies

### System Requirements

OS: Windows/Linux/macOS
RAM: Minimum 4GB (8GB recommended)
Storage: 1GB free space
Python: 3.11 recommended (3.8+ supported)



# Problem Statement
Healthcare provider credentialing accuracy is critical for patient safety, regulatory compliance, and operational efficiency. Errors in provider directories cost the healthcare industry over $3 billion annually and can lead to patient harm, claim denials, and compliance violations. This platform provides healthcare administrators with tools to quickly identify and resolve provider data quality issues through intelligent analytics and interactive interfaces.

# Architecture & Components
## 1. Data Processing Layer (dedupe_providers.py)
Purpose: Intelligent provider entity resolution and deduplication
Algorithm Logic:
Blocking Strategy

NPI Blocking: Groups providers by National Provider Identifier
License Blocking: Groups by license number and state combination
Name Blocking: Uses last name prefix (4 characters) for phonetic similarity
Phone Blocking: Groups by last 4 digits of practice phone
Taxonomy Blocking: Groups by medical specialty taxonomy codes

Similarity Scoring System
The algorithm uses a weighted scoring system:
Score Components:
- NPI Match: +6.0 points (highest weight - unique identifier)
- License Match: +5.0 points (state + license number)
- Name Similarity: +3.0 points (sequence matching)
- Token Overlap: +1.0 points (name token intersection)
- Phone Match: +1.5 points (last 4 digits)
- Address Overlap: +0.8 points (address token similarity)
- Taxonomy Match: +0.6 points (specialty codes)
- NPI Conflict: -4.0 points (different NPIs penalty)
Clustering Algorithm

Uses Union-Find data structure for efficient clustering
Definite Matches: Score ≥ 5.0 (automatic clustering)
Possible Matches: Score ≥ 3.0 (flagged for review)
Non-Matches: Score < 3.0 (separate entities)

Key Features:

Handles name variations, spelling differences, formatting inconsistencies
Prevents over-clustering through conflict detection
Generates detailed match explanations and confidence scores

## 2. Data Validation Layer (verification.py, dashboard.py)
Purpose: Cross-reference provider data with authoritative sources
Validation Components

License Validation

Cross-references with NY and CA medical board databases
Detects expired licenses, invalid numbers, specialty mismatches
Handles date format variations and parsing


NPI Verification

Validates against mock NPI registry
Checks for missing or incorrect NPIs
Verifies certification dates


Board Certification Logic
python# NY: Direct boolean comparison
if license_state == "NY":
    return "correct" if board_certified == "true" else specialty_value

### CA: Specialty matching against board_certification field
elif license_state == "CA":
    return "correct" if specialty == board_certification else mismatch_value

Data Quality Assessment

Field-by-field comparison with ground truth
Standardization of phone numbers, addresses
Missing data identification



Output: Creates roster_with_validations.csv with validation flags for each field
## 3. Database Layer (SQLite.py)
Purpose: Efficient querying infrastructure

Converts CSV data to SQLite database (roster.db)
Optimized for sub-2-second query response times
Supports complex filtering and aggregation queries
Maintains data integrity during conversion

## 4. Natural Language Processing (queries.py, chatapp.py)
Purpose: Convert natural language queries to SQL
Query Parser Architecture

Preprocessing Pipeline

Normalizes query variations
Extracts key entities (cities, states, specialties, years)
Handles temporal expressions


Entity Recognition
pythonSpecialty Mapping: "cardiologist" → "Cardiology"
State Mapping: "california" → "CA"  
City Mapping: "san francisco" → "SAN FRANCISCO" (exact case)
Years Parsing: "more than 20 years" → "> 20"

SQL Generation Logic

Detects query type (COUNT vs LIST)
Builds WHERE clauses based on extracted entities
Handles complex conditions (ranges, combinations)


Fallback System

Template matching using sentence transformers
Cosine similarity for best template selection
Graceful degradation for unrecognized queries



Example Transformations
"How many cardiologists in California with more than 15 years?"
→ "SELECT COUNT(*) FROM roster WHERE primary_specialty='Cardiology' 
   AND practice_state='CA' AND years_in_practice > 15"

"Show providers in San Francisco practicing for less than 5 years"
→ "SELECT * FROM roster WHERE practice_city='SAN FRANCISCO' 
   AND years_in_practice < 5 LIMIT 50"
   
## 5. User Interface Layer (app.py)
Purpose: Interactive dashboard and AI assistant
Dashboard Features

Executive Metrics: Provider counts, validation status, quality scores
Interactive Charts: Data quality summaries, geographic distributions
Real-time Activity: Recent validation events and updates

## AI Assistant Interface

Natural Language Chat: Process queries in conversational format
Sample Questions: Pre-built queries for common use cases
Result Export: Download query results as CSV
Visual Feedback: Color-coded responses and error handling


