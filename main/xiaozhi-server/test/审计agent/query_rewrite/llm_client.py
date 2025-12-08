import requests
import json
import logging
import subprocess
import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
from config import DEEPSEEK_API_URL, DEEPSEEK_API_KEY, DEEPSEEK_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekClient:
    def __init__(self, api_url=DEEPSEEK_API_URL, api_key=DEEPSEEK_API_KEY, model=DEEPSEEK_MODEL):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.0, stream: bool = False) -> Optional[str]:
        data = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature
        }
        
        # First try requests (with verify=False)
        try:
            # Suppress InsecureRequestWarning
            requests.packages.urllib3.disable_warnings()
            response = requests.post(self.api_url, headers=self.headers, json=data, timeout=60, verify=False)
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.warning(f"Requests failed ({e}), trying curl fallback...")
            return self._curl_fallback(data)
            
        return None

    def _curl_fallback(self, data: Dict) -> Optional[str]:
        try:
            json_data = json.dumps(data)
            
            cmd = [
                "curl",
                "--location",
                self.api_url,
                "--header",
                f"Authorization: Bearer {self.api_key}",
                "--header",
                "Content-Type: application/json",
                "--data",
                json_data,
                "--insecure"
            ]
            
            # On Windows, shell=False is safer, but sometimes needed for path resolution. 
            # Defaulting to False as per previous success.
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                logger.error(f"Curl failed with return code {result.returncode}: {result.stderr}")
                return None
                
            response_text = result.stdout
            try:
                response_json = json.loads(response_text)
                if 'choices' in response_json and len(response_json['choices']) > 0:
                    return response_json['choices'][0]['message']['content']
                else:
                    logger.error(f"Unexpected response format from curl: {response_text[:200]}...")
                    return None
            except json.JSONDecodeError:
                logger.error(f"Failed to decode curl response: {response_text[:200]}...")
                return None
                
        except Exception as curl_e:
            logger.error(f"Curl fallback also failed: {curl_e}")
            return None

    async def chat_completion_async(self, messages: List[Dict[str, str]], temperature: float = 0.0) -> Optional[str]:
        data = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": temperature
        }
        
        try:
            # Create a custom connector to disable SSL verification
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    self.api_url, 
                    headers=self.headers, 
                    json=data, 
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'choices' in result and len(result['choices']) > 0:
                            return result['choices'][0]['message']['content']
                    else:
                        logger.warning(f"Async request failed with status {response.status}, text: {await response.text()}")
                        # Fallback to curl in thread executor if aiohttp fails (e.g. proxy/network issues)
                        loop = asyncio.get_running_loop()
                        return await loop.run_in_executor(None, self._curl_fallback, data)
                        
        except Exception as e:
            logger.warning(f"Async aiohttp failed ({e}), trying curl fallback in thread...")
            try:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, self._curl_fallback, data)
            except Exception as e2:
                logger.error(f"Async curl fallback failed: {e2}")
                return None
