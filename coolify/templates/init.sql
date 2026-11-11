-- Bases et utilisateurs de la stack — version DÉPLOIEMENT DISTANT.
-- Générée par coolify/prepare.sh : les mots de passe viennent de coolify/coolify.env
-- et doivent correspondre aux variables DB_PASSWORD_* de coolify/templates/env/.

-- Une base et un utilisateur par service. Exécuté une seule fois,
-- au premier démarrage du volume PostgreSQL de la stack.
CREATE USER keycloak WITH PASSWORD '${DB_PASSWORD_KEYCLOAK}';
CREATE DATABASE keycloak OWNER keycloak;

CREATE USER docs WITH PASSWORD '${DB_PASSWORD_DOCS}';
CREATE DATABASE docs OWNER docs;

CREATE USER yhub WITH PASSWORD '${DB_PASSWORD_YHUB}';
CREATE DATABASE yhub OWNER yhub;

CREATE USER meet WITH PASSWORD '${DB_PASSWORD_MEET}';
CREATE DATABASE meet OWNER meet;

CREATE USER messages WITH PASSWORD '${DB_PASSWORD_MESSAGES}';
CREATE DATABASE messages OWNER messages;

CREATE USER projects WITH PASSWORD '${DB_PASSWORD_PROJECTS}';
CREATE DATABASE projects OWNER projects;

CREATE USER drive WITH PASSWORD '${DB_PASSWORD_DRIVE}';
CREATE DATABASE drive OWNER drive;

CREATE USER grist WITH PASSWORD '${DB_PASSWORD_GRIST}';
CREATE DATABASE grist OWNER grist;

CREATE USER transfers WITH PASSWORD '${DB_PASSWORD_TRANSFERS}';
CREATE DATABASE transfers OWNER transfers;

CREATE USER conversations WITH PASSWORD '${DB_PASSWORD_CONVERSATIONS}';
CREATE DATABASE conversations OWNER conversations;
