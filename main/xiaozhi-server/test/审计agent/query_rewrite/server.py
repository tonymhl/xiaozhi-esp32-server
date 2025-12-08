import json
import logging
import os
from aiohttp import web
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RESULTS_FILE = "evaluation_results.json"
HTML_FILE = "index.html"

async def handle_index(request):
    try:
        with open(HTML_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except Exception as e:
        return web.Response(text=str(e), status=500)

async def get_results(request):
    try:
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return web.json_response(data)
        else:
            return web.json_response({"error": "Results not found. Run evaluator first."}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def update_result(request):
    try:
        data = await request.json()
        item_id = data.get('id')
        verdict = data.get('verdict')
        
        if item_id is None or verdict not in ['pass', 'fail']:
            return web.json_response({"error": "Invalid input"}, status=400)
            
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
            
            # Find and update
            found = False
            for item in full_data.get('details', []):
                if item.get('id') == item_id:
                    item['final_verdict'] = verdict
                    item['human_reviewed'] = True
                    found = True
                    break
            
            if found:
                # Recalculate summary
                details = full_data.get('details', [])
                valid_cases = [d for d in details if d.get('expected') and len(d.get('expected')) > 0]
                passed_count = sum(1 for d in valid_cases if d.get('final_verdict') == 'pass')
                
                full_data['summary']['overall_accuracy'] = passed_count / len(valid_cases) if valid_cases else 0
                
                with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(full_data, f, ensure_ascii=False, indent=2)
                    
                return web.json_response({"status": "updated"})
            else:
                return web.json_response({"error": "Item not found"}, status=404)
        else:
            return web.json_response({"error": "Results file not found"}, status=404)
            
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

app = web.Application()
app.router.add_get('/', handle_index)
app.router.add_get('/api/results', get_results)
app.router.add_post('/api/update', update_result)

if __name__ == '__main__':
    web.run_app(app, port=8080)

