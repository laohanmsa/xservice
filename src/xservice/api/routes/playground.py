from fastapi import APIRouter, status
from fastapi.responses import HTMLResponse
from xservice.settings import settings

router = APIRouter()

# Kept inline to avoid introducing a template engine for one self-contained page.
HTML_CONTENT = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>xservice API Playground</title>
    <style>
        :root {{
            --bg-color: #2d2d2d;
            --text-color: #f0f0f0;
            --input-bg: #3c3c3c;
            --input-border: #555;
            --btn-bg: #007acc;
            --btn-text: #ffffff;
            --pre-bg: #1e1e1e;
            --border-radius: 4px;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 2rem;
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 1200px;
            width: 100%;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        .playground {{
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 2rem;
        }}
        .controls, .response {{
            background-color: var(--input-bg);
            padding: 1.5rem;
            border-radius: var(--border-radius);
            border: 1px solid var(--input-border);
        }}
        .control-group {{
            margin-bottom: 1.5rem;
        }}
        .operation-meta {{
            margin-bottom: 1.5rem;
            padding: 1rem;
            background-color: var(--bg-color);
            border: 1px solid var(--input-border);
            border-radius: var(--border-radius);
        }}
        .operation-meta h2 {{
            margin: 0 0 0.5rem;
            font-size: 1.1rem;
        }}
        .operation-meta p {{
            margin: 0;
            line-height: 1.5;
            color: #d0d0d0;
        }}
        label {{
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }}
        select, input[type="text"], textarea {{
            width: 100%;
            padding: 0.75rem;
            background-color: var(--bg-color);
            color: var(--text-color);
            border: 1px solid var(--input-border);
            border-radius: var(--border-radius);
            box-sizing: border-box;
            font-family: inherit;
            font-size: 1rem;
        }}
        textarea {{
            min-height: 150px;
            font-family: "Menlo", "Monaco", "Consolas", "Courier New", monospace;
        }}
        button {{
            width: 100%;
            padding: 0.8rem 1rem;
            background-color: var(--btn-bg);
            color: var(--btn-text);
            border: none;
            border-radius: var(--border-radius);
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
        }}
        button:hover {{
            background-color: #005a9e;
        }}
        pre {{
            background-color: var(--pre-bg);
            padding: 1rem;
            border-radius: var(--border-radius);
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: "Menlo", "Monaco", "Consolas", "Courier New", monospace;
        }}
        #response-headers, #response-body {{
            margin-top: 0.5rem;
        }}
        .response-status {{
            font-weight: bold;
            margin-bottom: 1rem;
        }}
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>xservice API Playground</h1>
        <div class="playground">
            <div class="controls">
                <div class="control-group">
                    <label for="api-key">API Key (X-API-KEY)</label>
                    <input type="text" id="api-key" value="{settings.PLAYGROUND_DEFAULT_API_KEY or ''}" placeholder="Your API Key">
                </div>

                <div class="control-group">
                    <label for="operation-selector">Select Operation</label>
                    <select id="operation-selector"></select>
                </div>

                <div id="operation-meta" class="operation-meta hidden">
                    <h2 id="operation-summary"></h2>
                    <p id="operation-description"></p>
                </div>

                <div id="parameters-container"></div>
                
                <div id="request-body-container" class="control-group hidden">
                    <label for="request-body">Request Body</label>
                    <textarea id="request-body"></textarea>
                </div>

                <button id="send-request-btn">Send Request</button>
            </div>
            <div class="response">
                <h2>Response</h2>
                <div id="response-container">
                    <div id="response-status"></div>
                    <div id="response-headers-container">
                        <label>Headers:</label>
                        <pre id="response-headers"></pre>
                    </div>
                     <div id="response-body-container">
                        <label>Body:</label>
                        <pre id="response-body"></pre>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const apiKeyInput = document.getElementById('api-key');
            const operationSelector = document.getElementById('operation-selector');
            const paramsContainer = document.getElementById('parameters-container');
            const operationMeta = document.getElementById('operation-meta');
            const operationSummaryElem = document.getElementById('operation-summary');
            const operationDescriptionElem = document.getElementById('operation-description');
            const requestBodyContainer = document.getElementById('request-body-container');
            const requestBodyInput = document.getElementById('request-body');
            const sendBtn = document.getElementById('send-request-btn');
            const responseStatusElem = document.getElementById('response-status');
            const responseHeadersElem = document.getElementById('response-headers');
            const responseBodyElem = document.getElementById('response-body');

            let openapiSpec = null;
            let selectedOperation = null;

            async function init() {{
                try {{
                    const response = await fetch('/openapi.json');
                    if (!response.ok) throw new Error('Failed to load OpenAPI spec.');
                    openapiSpec = await response.json();
                    populateOperations();
                    operationSelector.dispatchEvent(new Event('change'));
                }} catch (error) {{
                    console.error("Initialization Error:", error);
                    alert("Could not load API specification. Please check the console.");
                }}
            }}

            function populateOperations() {{
                if (!openapiSpec || !openapiSpec.paths) return;
                
                Object.entries(openapiSpec.paths).forEach(([path, methods]) => {{
                    Object.entries(methods).forEach(([method, details]) => {{
                        const operationId = details.operationId || `${{method.toUpperCase()}} ${{path}}`;
                        const option = new Option(`[${{method.toUpperCase()}}] ${{path}}`, operationId);
                        option.dataset.path = path;
                        option.dataset.method = method;
                        operationSelector.appendChild(option);
                    }});
                }});
            }}

            operationSelector.addEventListener('change', () => {{
                const selectedOption = operationSelector.options[operationSelector.selectedIndex];
                const {{ path, method }} = selectedOption.dataset;
                
                selectedOperation = {{
                    path,
                    method,
                    details: openapiSpec.paths[path][method],
                }};
                
                renderInputs();
            }});

            function renderInputs() {{
                paramsContainer.innerHTML = '';
                const summary = selectedOperation.details.summary || '';
                const description = selectedOperation.details.description || '';

                if (summary || description) {{
                    operationMeta.classList.remove('hidden');
                    operationSummaryElem.textContent = summary || 'Operation details';
                    operationDescriptionElem.textContent = description;
                }} else {{
                    operationMeta.classList.add('hidden');
                    operationSummaryElem.textContent = '';
                    operationDescriptionElem.textContent = '';
                }}
                
                const parameters = selectedOperation.details.parameters || [];
                parameters.forEach(param => {{
                    const group = document.createElement('div');
                    group.className = 'control-group';
                    const label = document.createElement('label');
                    label.textContent = `${{param.name}} (${{param.in}})`;
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.dataset.name = param.name;
                    input.dataset.in = param.in;
                    input.placeholder = param.schema.title || param.name;
                    group.appendChild(label);
                    group.appendChild(input);
                    paramsContainer.appendChild(group);
                }});

                if (selectedOperation.details.requestBody) {{
                    requestBodyContainer.classList.remove('hidden');
                    const schema = selectedOperation.details.requestBody.content['application/json'].schema;
                    requestBodyInput.value = JSON.stringify(schema, null, 2);
                }} else {{
                    requestBodyContainer.classList.add('hidden');
                    requestBodyInput.value = '';
                }}
            }}

            sendBtn.addEventListener('click', async () => {{
                if (!selectedOperation) return;

                let path = selectedOperation.path;
                const queryParams = new URLSearchParams();
                
                paramsContainer.querySelectorAll('input').forEach(input => {{
                    const name = input.dataset.name;
                    const value = input.value.trim();
                    const paramIn = input.dataset.in;

                    if (value) {{
                        if (paramIn === 'path') {{
                            path = path.replace(`{{${{name}}}}`, encodeURIComponent(value));
                        }} else if (paramIn === 'query') {{
                            queryParams.append(name, value);
                        }}
                    }}
                }});

                const queryString = queryParams.toString();
                const finalUrl = queryString ? `${{path}}?${{queryString}}` : path;
                
                const headers = {{
                    'Accept': 'application/json',
                }};
                const apiKey = apiKeyInput.value.trim();
                if (apiKey) {{
                    headers['X-API-KEY'] = apiKey;
                }}
                
                const fetchOptions = {{
                    method: selectedOperation.method.toUpperCase(),
                    headers: headers,
                }};

                if (!requestBodyContainer.classList.contains('hidden') && requestBodyInput.value) {{
                    try {{
                        JSON.parse(requestBodyInput.value); // Validate JSON
                        headers['Content-Type'] = 'application/json';
                        fetchOptions.body = requestBodyInput.value;
                    }} catch (e) {{
                        alert('Request body is not valid JSON.');
                        return;
                    }}
                }}
                
                // Clear previous response
                responseStatusElem.textContent = 'Loading...';
                responseHeadersElem.textContent = '';
                responseBodyElem.textContent = '';

                try {{
                    const response = await fetch(finalUrl, fetchOptions);
                    
                    const statusText = `Status: ${{response.status}} ${{response.statusText}}`;
                    responseStatusElem.textContent = statusText;
                    
                    const responseHeaders = {{}};
                    response.headers.forEach((value, key) => {{
                        responseHeaders[key] = value;
                    }});
                    responseHeadersElem.textContent = JSON.stringify(responseHeaders, null, 2);

                    const rawBody = await response.text();
                    try {{
                        const responseBody = JSON.parse(rawBody);
                        responseBodyElem.textContent = JSON.stringify(responseBody, null, 2);
                    }} catch (_error) {{
                        responseBodyElem.textContent = rawBody;
                    }}
                }} catch (error) {{
                    responseStatusElem.textContent = 'Error';
                    responseBodyElem.textContent = error.message;
                    console.error('Request failed:', error);
                }}
            }});

            init();
        }});
    </script>
</body>
</html>
"""

@router.get("/playground", response_class=HTMLResponse, status_code=status.HTTP_200_OK, tags=["playground"], summary="Serves the API playground.")
async def get_playground():
    """
    Serves a simple, self-contained HTML page that acts as an API playground.

    This playground allows users to interact with the API endpoints defined in the
    OpenAPI specification (`/openapi.json`). It dynamically builds controls
    for each operation, including path/query parameters and request bodies.
    """
    return HTMLResponse(content=HTML_CONTENT)
