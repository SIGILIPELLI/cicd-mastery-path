from jenkinslint import lint, balanced, strip_comments_and_strings
GOOD = open("Jenkinsfile").read()
def has(p, s): return any(s in x for x in p)
def test_good_is_clean(): assert lint(GOOD) == []
def test_unbalanced(): assert has(lint(GOOD + "}"), "unbalanced")
def test_braces_in_strings_do_not_count(): assert balanced("pipeline { stages { stage('x') { steps { echo '}}}' } } } }")
def test_comments_ignored(): assert "timeout" not in strip_comments_and_strings("// timeout(time: 1)\n/* timeout( */ pipeline {}")
def test_agent_any(): assert has(lint(GOOD.replace("agent { label 'linux && docker' }", "agent any")), "agent any")
def test_no_timeout(): assert has(lint(GOOD.replace("timeout(time: 30, unit: 'MINUTES')", "")), "timeout")
def test_no_post(): assert has(lint(GOOD[:GOOD.index("    post {")] + "}\n"), "post")
def test_hardcoded_secret(): assert has(lint(GOOD.replace('APP_VERSION =', 'DB_PASSWORD = "hunter2hunter2"\n        APP_VERSION =')), "hard-coded credential")
def test_deploy_without_when(): assert has(lint(GOOD.replace("when { branch 'main' }", "")), "looks like a deployment")
def test_secret_in_groovy_string():
    bad = GOOD.replace("sh './deploy.sh staging \"$TOKEN\"'", 'sh "./deploy.sh staging ${TOKEN}"'); assert has(lint(bad), "interpolated")
def test_missing_stages(): assert has(lint("pipeline { agent { label 'x' } options { timeout(time: 1) } post { always { echo 'x' } } }"), "stages")
