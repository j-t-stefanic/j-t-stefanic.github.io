---
layout: default
title: Wine Catalog Data Platform | John Stefanic
---
[← Back to Portfolio](../)

# 🍷 Wine Catalog Data Platform
**Python · MySQL · MongoDB · React · OCR · ETL · Data Quality**

## Project Overview
An end-to-end data project that transforms wine labels, scanned PDFs, images, and structured source files into a clean, searchable catalog.

## The Challenge
Records from multiple formats needed to be standardized, matched, checked for duplicates, enriched with missing information, linked to bottle images, and prepared for a searchable application.

## Solution Architecture
Wine Labels / PDFs / Images → Extraction & Matching → Cleaning & Validation → MySQL → MongoDB → API → React Catalog

## Key Work
- Extracted wine name, producer, vintage, URL, UPC, category, country, region, and image information.
- Generated SQL INSERT statements for cleaned records.
- Compared datasets using wine name, producer, and vintage to identify duplicates.
- Enriched missing producer URLs and corrected producer mappings.
- Matched missing image references to extracted label information.
- Loaded and compared records in MongoDB collections.
- Audited image paths to identify missing assets.
- Developed a React/MongoDB catalog workflow with filtering and image display.

## Data Quality Focus
Validation includes duplicate checks, category validation, missing-image audits, producer URL review, record matching, and cross-database comparisons.

## Skills Demonstrated
Python · SQL · MySQL · MongoDB · ETL · OCR Workflows · Data Cleaning · Data Validation · React · REST APIs

[← Back to Portfolio](../)
