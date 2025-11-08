# ✅ GitHub CI/CD Testing Checklist

## Phase 1: GitHub Repository Setup (5 minutes)

### 1. Create GitHub Repository
- [ ] Go to GitHub.com and create new repository
- [ ] Repository name: "flashcard-study-app" (or preferred name)
- [ ] Description: "AI-powered flashcard study app with spaced repetition"
- [ ] Set to Public repository (for unlimited GitHub Actions)
- [ ] DON'T initialize with README (we have files already)
- [ ] Copy the repository URL

### 2. Initialize Git and Connect to GitHub
- [ ] Run `git init` (if not already done)
- [ ] Run `git add .` to stage all files
- [ ] Create initial commit with `git commit -m "Initial commit: Flashcard study app..."`
- [ ] Add remote: `git remote add origin https://github.com/yourusername/flashcard-study-app.git`
- [ ] Set default branch: `git branch -M main`
- [ ] Initial push: `git push -u origin main`

---

## Phase 2: GitHub Configuration (5 minutes)

### 3. Set Up GitHub Secrets (Required for Tests)
- [ ] Go to Repository → Settings → Secrets and variables → Actions
- [ ] Add `ANTHROPIC_API_KEY` = sk-ant-your-anthropic-key-here
- [ ] Add `OPENAI_API_KEY` = sk-your-openai-key-here

### 4. Set Up Branch Protection (Optional)
- [ ] Go to Repository → Settings → Branches
- [ ] Add protection rule for `main` branch
- [ ] ✅ Require a pull request before merging
- [ ] ✅ Require status checks to pass before merging
- [ ] Select status checks: `Run Tests` and `Code Quality`

---

## Phase 3: CI/CD Testing (10 minutes)

### 5. Test CI/CD Pipeline
- [ ] Create test branch: `git checkout -b test/ci-cd-validation`
- [ ] Make small change: `echo "# Testing CI/CD Pipeline" >> README.md`
- [ ] Stage and commit: `git add README.md && git commit -m "test: Validate CI/CD pipeline functionality"`
- [ ] Push test branch: `git push -u origin test/ci-cd-validation`

### 6. Create Test Pull Request
- [ ] Go to GitHub → Your Repository → Pull Requests → New Pull Request
- [ ] Select: `test/ci-cd-validation` → `main`
- [ ] Title: "Test: Validate CI/CD Pipeline"
- [ ] Description: "Testing automated workflows - lint and test checks"
- [ ] Create Pull Request

### 7. Verify CI/CD Results
- [ ] ✅ **Tests workflow runs automatically**
- [ ] ✅ **All 129 tests pass** (PostgreSQL + SQLite compatibility)
- [ ] ✅ **Code quality checks pass** (ruff linting)
- [ ] ✅ **Type checking passes** (mypy)
- [ ] ✅ **Security scan completes** (Trivy)
- [ ] ✅ **Docker build test succeeds**
- [ ] ✅ **All status checks are green**

---

## 🎯 Success Criteria

Mark as complete when ALL items below are ✅:

- [ ] **✅ GitHub repository created and code pushed**
- [ ] **✅ GitHub Actions workflow triggers on PR**
- [ ] **✅ All 129 tests pass** in CI pipeline
- [ ] **✅ Linting passes** (ruff check with 0 issues)
- [ ] **✅ Type checking passes** (mypy validation)
- [ ] **✅ Security scan completes** (no critical vulnerabilities)
- [ ] **✅ Docker builds succeed** (development and production targets)
- [ ] **✅ No workflow failures** (all green checkmarks)

---

## 🚨 Troubleshooting Reference

### GitHub Actions Failing
- [ ] Check workflow logs in GitHub Actions tab
- [ ] Verify API keys are added: Repository → Settings → Secrets
- [ ] Common issue: Missing `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- [ ] Check if PostgreSQL service starts correctly in CI

### Test Failures
- [ ] Review test output in GitHub Actions logs
- [ ] Most likely: Database connection issues in CI
- [ ] Verify environment variables are available in workflow
- [ ] Check if all dependencies install correctly

### Linting Failures
- [ ] Run locally: `uv run ruff check .`
- [ ] Fix issues: `uv run ruff check --fix .`
- [ ] Format code: `uv run ruff format .`
- [ ] Commit and push fixes

### Docker Build Issues
- [ ] Check .dockerignore includes correct files
- [ ] Verify all dependencies are in pyproject.toml
- [ ] Test locally: `docker build --target development .`

---

## 🎉 Completion

### Clean Up
- [ ] Merge the successful test PR (optional)
- [ ] Clean up test branch: `git branch -d test/ci-cd-validation`
- [ ] Mark CI/CD as ✅ **WORKING**

### Next Steps
- [ ] CI/CD infrastructure is verified and working
- [ ] Ready to continue with feature development
- [ ] Can add deployment phases later when needed

---

**✅ CI/CD PIPELINE: [ ] COMPLETE**

*Check this box when all tests pass and code quality checks are green!*