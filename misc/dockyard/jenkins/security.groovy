import jenkins.model.*
import hudson.security.*

def instance = Jenkins.getInstance()

println "[Jenkins-Init] Creating Algerian Devs default admin operator..."

// Set up security realm and create admin user
def hudsonRealm = new HudsonPrivateSecurityRealm(false)
hudsonRealm.createAccount("admin", "4mdj4d_dz_sec_2026")
instance.setSecurityRealm(hudsonRealm)

// Grant full control to logged in users
def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
instance.setAuthorizationStrategy(strategy)

instance.save()
println "[Jenkins-Init] Initialization complete. Credentials set to admin / 4mdj4d_dz_sec_2026."
