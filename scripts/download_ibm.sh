#!/usr/bin/env bash
# Download IBM's synthetic AML transactions (HI-Small, ~5M rows, ~475 MB) from Kaggle.
# One-time setup: kaggle.com -> Settings -> API -> "Create New Token",
# then save kaggle.json to ~/.kaggle/kaggle.json (chmod 600).
set -euo pipefail

DEST="${AML_DATA_DIR:-./data}/raw"
mkdir -p "$DEST"

if [[ -f "$DEST/HI-Small_Trans.csv" ]]; then
  echo "Already downloaded: $DEST/HI-Small_Trans.csv"
  exit 0
fi

uv run --with kaggle kaggle datasets download \
  -d ealtman2019/ibm-transactions-for-anti-money-laundering-aml \
  -f HI-Small_Trans.csv -p "$DEST"

# Kaggle zips single files.
if [[ -f "$DEST/HI-Small_Trans.csv.zip" ]]; then
  unzip -o "$DEST/HI-Small_Trans.csv.zip" -d "$DEST" && rm "$DEST/HI-Small_Trans.csv.zip"
fi
echo "Saved to $DEST/HI-Small_Trans.csv"
