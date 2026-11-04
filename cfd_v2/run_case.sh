#!/usr/bin/env bash
# Mesh, solve and post-process one cfd_v2 case.  Usage:
#   bash cfd_v2/run_case.sh CASE_DIR [NPROCS]
# Stops at the first failed step. Logs go to CASE_DIR/log.*
set -euo pipefail
CASE=$(realpath "$1"); NP=${2:-1}
HERE=$(dirname "$(realpath "$0")")
# Ubuntu's openfoam package (v1912) installs the binaries in /usr/bin
if ! command -v pimpleFoam >/dev/null; then echo "OpenFOAM not found: source your etc/bashrc first"; exit 1; fi
export WM_PROJECT_DIR=${WM_PROJECT_DIR:-/usr/share/openfoam}
export FOAM_ETC=${FOAM_ETC:-$WM_PROJECT_DIR/etc}
cd "$CASE"
step() { echo "== $1"; shift; "$@" > "log.$STEP" 2>&1 || { echo "FAILED: see $CASE/log.$STEP"; exit 1; }; }

if [ ! -d constant/polyMesh ] || [ ! -f constant/polyMesh/owner ]; then
  STEP=blockMesh step "background mesh" blockMesh
  STEP=snappyHexMesh step "snappyHexMesh (snap + layers)" snappyHexMesh -overwrite
fi
STEP=checkMesh step "checkMesh" checkMesh
STEP=checkMesh.full step "checkMesh -allGeometry (for the record)" checkMesh -allTopology -allGeometry
# Gate: 'Mesh OK.', or the only failure is a few highly skewed faces (common next to prism layers).
# Anything else (negative volumes, wrong orientation, open cells) stops the run.
if ! grep -q "Mesh OK." log.checkMesh; then
  if grep "^ \*\*\*" log.checkMesh | grep -qv "skewness"; then
    echo "checkMesh failed (see log.checkMesh)"; exit 1; fi
  echo "WARNING: only skewness failed in checkMesh; inspect the skewed faces before trusting WSS nearby"
fi
# a mesh that kept outer-box faces leaked outside the vessel
if grep -A3 -E "^\s*box\s*$" constant/polyMesh/boundary | grep -qE "nFaces\s+[1-9]"; then
  echo "Mesh leaked: outer box faces remain"; exit 1; fi
grep -E "^\s+cells:|Max non-orthogonality|Max skewness" log.checkMesh || true
# layer coverage: how much of the wall got prism layers
grep -A8 "layers   overall thickness" log.snappyHexMesh 2>/dev/null | tail -8 || true

if [ -f log.pimpleFoam ]; then echo "A solve already exists here; use a new case folder"; exit 1; fi
if [ "$NP" -gt 1 ]; then
  # 'simple' slices along z (the vessel axis); Ubuntu's package has no scotch library
  printf 'FoamFile {version 2.0; format ascii; class dictionary; object decomposeParDict;}\nnumberOfSubdomains %s;\nmethod simple;\nsimpleCoeffs {n (1 1 %s); delta 0.001;}\n' "$NP" "$NP" > system/decomposeParDict
  STEP=decomposePar step "decompose" decomposePar -force
  STEP=pimpleFoam step "solve on $NP cores (hours)" mpirun -np "$NP" pimpleFoam -parallel
  STEP=reconstructPar step "reconstruct" reconstructPar
else
  STEP=pimpleFoam step "solve (hours)" pimpleFoam
fi
grep -q "^End" log.pimpleFoam || { echo "Solver did not finish"; exit 1; }
# OpenFOAM's own WSS output is optional: Ubuntu's v1912 package crashes here ('sha1' error),
# and analyze_case.py then computes WSS from the wall-cell velocities instead.
echo "== wall shear stress (OpenFOAM, optional)"
pimpleFoam -postProcess -func wallShearStress -noZero > log.wallShearStress 2>&1 \
  || echo "   OpenFOAM wallShearStress failed (known in Ubuntu's package); WSS will be computed from velocity"
STEP=analyze step "TAWSS/OSI/RRT" python3 "$HERE/analyze_case.py" "$CASE"
cat results/summary.json
