from flask import Blueprint, request, jsonify
from datetime import datetime
from app.extensions import collections  # MongoDB collection instance

# Create a Flask Blueprint for webhook-related routes
webhook = Blueprint('Webhook', __name__, url_prefix='/webhook')


# Home page route that displays the latest 10 events in a table
@webhook.route('/', methods=['GET'])
def home():
    events = list(collections.find().sort("timestamp", -1).limit(10))
    # Convert ObjectId to string for display
    for e in events:
        e["_id"] = str(e["_id"])
    # Build HTML table
    table_rows = "".join([
        f"<tr><td>{e.get('author','')}</td><td>{e.get('action','')}</td><td>{e.get('from_branch','')}</td><td>{e.get('to_branch','')}</td><td>{e.get('timestamp','')}</td></tr>"
        for e in events
    ])
    html = f'''
    <h1>Welcome to the GitHub Webhook Dashboard</h1>
    <p>Showing the latest 10 events:</p>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><th>Author</th><th>Action</th><th>From Branch</th><th>To Branch</th><th>Timestamp</th></tr>
        {table_rows}
    </table>
    <p>For a live dashboard, visit <a href="/webhook/ui">/webhook/ui</a>.</p>
    '''
    return html


# Route to get the latest 10 GitHub event documents from MongoDB
@webhook.route("/events", methods=["GET"])
def get_events():
    # Fetch last 10 documents sorted by descending timestamp (newest first)
    events = list(collections.find().sort("timestamp", -1).limit(10))

    # Convert ObjectId to string for JSON serialization
    for e in events:
        e["_id"] = str(e["_id"])
    return jsonify(events)  # Return the list as a JSON response


# Route to serve a simple HTML page that displays GitHub events
@webhook.route("/ui")
def ui():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>GitHub Webhook Events</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f4f4f4; }
            .event { background: white; margin: 10px 0; padding: 10px; border-left: 5px solid #007BFF; }
        </style>
    </head>
    <body>
        <h2>Recent GitHub Events</h2>
        <div id="event-list">Loading...</div>

        <script>
            // Asynchronous function to fetch and display recent events
            async function loadEvents() {
                const res = await fetch('/webhook/events');  // Fetch data from /events endpoint
                const data = await res.json();               // Parse the JSON response
                const container = document.getElementById('event-list');   

                // Create and display HTML based on each event type
                container.innerHTML = data.map(event => {
                    const time = new Date(event.timestamp).toLocaleString();
                    if (event.action === "PUSH") {
                        return `<div class="event"><b>${event.author}</b> pushed to <b>${event.to_branch}</b> at ${time}</div>`;
                    } else if (event.action === "PULL_REQUEST") {
                        return `<div class="event"><b>${event.author}</b> opened a PR from <b>${event.from_branch}</b> to <b>${event.to_branch}</b> at ${time}</div>`;
                    } else if (event.action === "MERGE") {
                        return `<div class="event"><b>${event.author}</b> merged <b>${event.from_branch}</b> to <b>${event.to_branch}</b> at ${time}</div>`;
                    }
                    return '';
                }).join('');
            }

            loadEvents();                   // Initial load of events
            setInterval(loadEvents, 15000); // Auto-refresh every 15 seconds
        </script>
    </body>
    </html>
    '''


# Route to receive and process GitHub webhook POST requests
@webhook.route('/receiver', methods=["POST"])
def receiver():
    try:
        if not request.is_json:
            print("Invalid content type or empty payload.")
            return jsonify({'error': 'Invalid content type or empty payload.'}), 400
        data = request.get_json(silent=True)
        print("Payload received:", data)
        if not data:
            return jsonify({'error': 'No JSON payload received.'}), 400

        # Identify the event type from GitHub headers
        event = request.headers.get('X-GitHub-Event', 'ping')
        print("Event Type:", event)

        # Handle 'push' events
        if event == 'push':
            pusher = data.get('pusher', {})
            author = pusher.get('name', 'unknown')
            ref = data.get('ref', '')
            to_branch = ref.split('/')[-1] if ref else 'unknown'

            # Loop through all commits and store each as a separate document
            for commit in data.get('commits', []):
                document = {
                    'request_id': commit.get('id', ''),
                    'author': author,
                    'action': "PUSH",
                    'from_branch': None,
                    'to_branch': to_branch,
                    'timestamp': commit.get('timestamp', datetime.utcnow().isoformat())
                }
                collections.insert_one(document)  # Insert into MongoDB
                print("Saved commit document:", document)

        # Handle 'pull_request' events
        elif event == 'pull_request':
            pr = data.get('pull_request')
            action = data.get('action')  # e.g., 'opened', 'closed'
            if not pr or not action:
                print("Missing pull_request or action in payload.")
                return '', 204
            document = {
                'request_id': str(pr.get('id', '')),
                'author': pr.get('user', {}).get('login', 'unknown'),
                'action': None,
                'from_branch': pr.get('head', {}).get('ref', ''),  # Source branch
                'to_branch': pr.get('base', {}).get('ref', ''),    # Target branch
                'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')  # Current time in ISO format
            }

            # Determine the specific PR action
            if action == 'opened':
                document['action'] = "PULL_REQUEST"
            elif action == 'closed' and pr.get('merged'):
                document['action'] = "MERGE"
            else:
                return '', 204  # Ignore irrelevant PR actions

            collections.insert_one(document)  # Insert into MongoDB
            print("Saved PR document:", document)

        else:
            print(f"Unhandled event type: {event}")
            return '', 204  # Ignore unhandled events

        return "Receiver Work Successfully", 200  # Acknowledge receipt

    except Exception as e:
        # Handle and log any errors
        print("ERROR:", e)
        return jsonify({'error': str(e)}), 500