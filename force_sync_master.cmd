chcp 1251
cd "C:/git_reps/google-cloud-python"
git checkout master
git fetch upstream
git reset upstream/master --hard
git push origin --force