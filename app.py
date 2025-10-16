import base64
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_file
from flask_cors import CORS
import io
import pytz

# Initialize the Flask app
app = Flask(__name__)
CORS(app) # Enable Cross-Origin Resource Sharing

# --- In-memory database ---
# In a real-world application, you would use a proper database like PostgreSQL or Redis.
# For this example, we'll use a simple dictionary to store tracking data.
# The structure will be: { "tracking_id": {"campaign": "campaign_name", "events": []} }
tracked_emails = {}

# --- The Tracking Pixel ---
# This is a 1x1 transparent GIF. It's tiny and won't be visible in the email.
# We decode it from base64 to serve it directly from memory.
PIXEL_GIF_B64 = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
PIXEL_GIF_DATA = base64.b64decode(PIXEL_GIF_B64)

def get_current_time():
    """Returns the current time in US/Pacific timezone for consistency."""
    return datetime.now(pytz.timezone('US/Pacific')).strftime('%Y-%m-%d %I:%M:%S %p %Z')

@app.route('/')
def index():
    """Serves the main dashboard page."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_pixel():
    """Generates a new unique tracking ID and URL for a campaign."""
    campaign = request.json.get('campaign', 'Untitled Campaign')
    tracking_id = str(uuid.uuid4())
    
    # Store the new tracking ID and campaign name
    tracked_emails[tracking_id] = {
        "campaign": campaign,
        "events": []
    }
    
    # The full URL for the tracking pixel
    # In production on Render, request.host_url will be your live URL
    tracking_url = f"{request.host_url}track/{tracking_id}"
    
    return jsonify({
        'tracking_id': tracking_id,
        'tracking_url': tracking_url,
        'html_snippet': f'<img src="{tracking_url}" width="1" height="1" alt="">'
    })

@app.route('/track/<tracking_id>')
def track_email(tracking_id):
    """This is the endpoint the email client hits. It logs the 'open' and serves the pixel."""
    if tracking_id in tracked_emails:
        # --- Log the open event ---
        event_data = {
            'ip_address': request.headers.get('X-Forwarded-For', request.remote_addr),
            'user_agent': request.headers.get('User-Agent'),
            'timestamp': get_current_time()
        }
        tracked_emails[tracking_id]['events'].append(event_data)
        print(f"Tracked open for ID: {tracking_id} from IP: {event_data['ip_address']}")

    # --- Serve the 1x1 transparent GIF ---
    # We serve the raw image data directly.
    return send_file(
        io.BytesIO(PIXEL_GIF_DATA),
        mimetype='image/gif',
        as_attachment=False,
        download_name='pixel.gif'
    )

@app.route('/events')
def get_events():
    """API endpoint for the frontend to fetch all tracking data."""
    # We'll format the data to be easily displayed in a table.
    all_events = []
    for track_id, data in tracked_emails.items():
        for event in data['events']:
            all_events.append({
                'campaign': data.get('campaign', 'N/A'),
                'track_id': track_id,
                'timestamp': event['timestamp'],
                'ip_address': event['ip_address'],
                'user_agent': event['user_agent']
            })
            
    # Sort events by timestamp, most recent first
    sorted_events = sorted(all_events, key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %I:%M:%S %p %Z'), reverse=True)
    
    return jsonify(sorted_events)

# This is necessary for Render's health checks and to run the app
if __name__ == '__main__':
    # The host must be '0.0.0.0' to be accessible within Render's container
    app.run(host='0.0.0.0', port=5000)
