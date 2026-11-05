cd ~/MT && . .venv-lab/bin/activate
N=175
PYTHONPATH=app python -m unittest discover -s tests > ~/t.log 2>&1 ; echo VENV=$?
grep -E "^FAIL:|^ERROR:|^Ran |^OK|^FAILED" ~/t.log
./scripts/test.sh > ~/test-mt.log 2>&1 ; echo TEST=$?
grep -E "^FAIL:|^ERROR:|^Ran |^OK|^FAILED" ~/test-mt.log
if grep -q "^Ran $N " ~/t.log && grep -q "^OK" ~/t.log && grep -q "^Ran $N " ~/test-mt.log && grep -q "^OK" ~/test-mt.log; then
  if git add -A app tests compose.yaml && git commit -q -m "simple: aucune case cochee au depart en 1, video deja coupee rouverte sans redecoupe (memes options), tests"; then
    git log --oneline -n 1 && echo COMMIT_OK
    git bundle create ~/MT-simple.bundle --all >/dev/null 2>&1 && echo BUNDLE_OK || echo BUNDLE_FAIL
  else echo COMMIT_FAIL ; fi
else echo COMMIT_SKIP ; fi
git status -sb | head -n 3
