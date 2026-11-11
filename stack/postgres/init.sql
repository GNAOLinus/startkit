-- Une base et un utilisateur par service. Exécuté une seule fois,
-- au premier démarrage du volume PostgreSQL de la stack.
CREATE USER keycloak WITH PASSWORD 'keycloak';
CREATE DATABASE keycloak OWNER keycloak;

CREATE USER docs WITH PASSWORD 'docs';
CREATE DATABASE docs OWNER docs;

CREATE USER yhub WITH PASSWORD 'yhub';
CREATE DATABASE yhub OWNER yhub;

CREATE USER meet WITH PASSWORD 'meet';
CREATE DATABASE meet OWNER meet;

CREATE USER messages WITH PASSWORD 'messages';
CREATE DATABASE messages OWNER messages;

CREATE USER projects WITH PASSWORD 'projects';
CREATE DATABASE projects OWNER projects;

CREATE USER drive WITH PASSWORD 'drive';
CREATE DATABASE drive OWNER drive;

CREATE USER grist WITH PASSWORD 'grist';
CREATE DATABASE grist OWNER grist;

CREATE USER transfers WITH PASSWORD 'transfers';
CREATE DATABASE transfers OWNER transfers;

CREATE USER conversations WITH PASSWORD 'conversations';
CREATE DATABASE conversations OWNER conversations;
