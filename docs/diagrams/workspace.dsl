workspace "The All Seeing Eye" "Logical application architecture, independent of any deployed host." {
    model {
        researcher = person "Researcher" "Explores observations, asks questions and reviews saved evidence."
        administrator = person "Administrator" "Manages access, source connections and AI configuration."
        sources = softwareSystem "Public sources" "Feeds, APIs, catalogues and reference data." "External"
        ai = softwareSystem "Configured AI provider" "Optional language, vision and embedding capabilities." "External"
        mail = softwareSystem "Email service" "Optional account messages and email verification." "External"
        ase = softwareSystem "The All Seeing Eye" "Self-hosted OSINT collection, research and evidence review." {
            browser = container "Browser application" "Globe, research, reports and administration." "React, TypeScript, MapLibre, deck.gl" "Browser"
            web = container "Web server" "Serves the browser application and proxies API traffic." "Caddy"
            api = container "Application API" "Collection, live memory store, research, access policy and background jobs. One API process." "Python, FastAPI"
            database = container "Database" "Accounts, configuration, briefs, jobs, report versions and selected evidence." "PostgreSQL; SQLite in native development" "Database"
            parser = container "Isolated file parser" "Bounded extraction of supplied documents and media. No network in Compose." "Python worker"
        }
        researcher -> browser "Uses"
        administrator -> browser "Administers"
        browser -> web "Loads UI and calls API" "HTTPS / JSON / SSE"
        web -> api "Proxies requests and streams" "HTTP"
        api -> database "Saves durable records" "SQLAlchemy"
        api -> parser "Extracts supplied files" "Local socket in Compose"
        api -> sources "Collects public information" "HTTPS / provider protocols"
        api -> ai "Sends selected context; receives model output" "HTTPS"
        api -> mail "Sends account messages when configured" "SMTP with TLS"
    }
    views {
        systemContext ase "system-context" {
            include *
            autolayout lr
        }
        container ase "containers" {
            include *
            exclude researcher administrator mail
            autolayout lr
        }
        styles {
            element "Element" {
                background #24364b
                color #ffffff
            }
            element "Person" {
                shape Person
                background #145a71
            }
            element "External" {
                background #596579
            }
            element "Database" {
                shape Cylinder
            }
            element "Browser" {
                shape WebBrowser
            }
        }
    }
}
