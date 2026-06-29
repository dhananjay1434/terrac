#!/bin/bash
# CI script to strictly ensure no demo mode magic values are present in production code.

if grep -rn "DMRV_DEMO_MODE" lib/ | grep -v "kReleaseMode"; then
  echo "ERROR: Found DMRV_DEMO_MODE without kReleaseMode guard!"
  exit 1
fi
echo "OK: Demo mode properly guarded."
exit 0
