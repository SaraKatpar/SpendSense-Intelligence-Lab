# Dataset provenance

## Household transactions

Proposal dataset: Daily Household Transactions, 2,461 raw records.
Retrieved public CSV mirror:
https://github.com/sanjanakrishnaraj0-lang/Daily-Transaction-Analysis
File: `Daily Household Transactions.csv`.
The mirror identifies Kaggle as its upstream source; its exact original Kaggle
dataset URL is not supplied in the submitted screenshot. Confirm that attribution
with the team before the final report. Do not claim the mirror is the original author.
Source currency is INR, not PKR. No user IDs are provided. Transfer-Out records
are excluded from expense totals. Cleaned data and explicit mapping are provided.

## Receipt benchmark

ICDAR 2019 SROIE challenge:
https://github.com/zzzDavid/ICDAR-2019-SROIE
Paper: https://arxiv.org/abs/2103.10213
The code supports image files with matching SROIE entity JSON annotations.
The full benchmark is not bundled; respect upstream dataset access/licensing.

## Spending-mix references

Household, original Berka ASC and the publisher-described real Personal Finance reference are the only sources used by the rebuilt research clusters. Personal source monetary units are unspecified. See ../eval/spending_mix_v1/REPORT.md and its metadata reviews. No generated sample is used for training, evaluation or demonstrations. Removed-source hashes are recorded in the retirement manifest.
