import base64
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_file
from flask_cors import CORS
import io
import pytz

app = Flask(__name__)
CORS(app)

tracked_emails = {}

PIXEL_GIF_B64 = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
PIXEL_GIF_DATA = base64.b64decode(PIXEL_GIF_B64)

# THE FIX IS HERE: Removed the %Z from the format string
TIME_FORMAT = '%Y-%m-%d %I:%M:%S %p'

def get_current_time():
    """Returns the current time in US/Pacific timezone for consistency."""
    return datetime.now(pytz.timezone('US/Pacific')).strftime(TIME_FORMAT)

@app.route('/')
def index():
    """Serves the main dashboard page."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_pixel():
    """Generates a new unique tracking ID and URL for a campaign."""
    campaign = request.json.get('campaign', 'Untitled Campaign')
    tracking_id = str(uuid.uuid4())
    
    tracked_emails[tracking_id] = {
        "campaign": campaign,
        "events": []
    }
    
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
        event_data = {
            'ip_address': request.headers.get('X-Forwarded-For', request.remote_addr),
            'user_agent': request.headers.get('User-Agent'),
            'timestamp': get_current_time()
        }
        tracked_emails[tracking_id]['events'].append(event_data)
        print(f"Tracked open for ID: {tracking_id} from IP: {event_data['ip_address']}")

    return send_file(
        io.BytesIO(PIXEL_GIF_DATA),
        mimetype='image/gif',
        as_attachment=False,
        download_name='pixel.gif'
    )

@app.route('/events')
def get_events():
    """API endpoint for the frontend to fetch all tracking data."""
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
    
    # THE FIX IS HERE: Use the new TIME_FORMAT for sorting
    sorted_events = sorted(all_events, key=lambda x: datetime.strptime(x['timestamp'], TIME_FORMAT), reverse=True)
    
    return jsonify(sorted_events)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
