const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const providerSelect = document.getElementById('provider-select');
const apiKeyInput = document.getElementById('api-key-input');
const saveSettingsBtn = document.getElementById('save-settings-btn');

// Load settings from chrome.storage
function loadSettings() {
  if (!chrome || !chrome.storage) return; // fallback for local dev
  chrome.storage.sync.get(['provider', 'apiKey'], (data) => {
    if (data.provider) providerSelect.value = data.provider;
    if (data.apiKey) apiKeyInput.value = data.apiKey;
    updateChatInputState();
  });
}

// Save settings to chrome.storage
function saveSettings() {
  const provider = providerSelect.value;
  const apiKey = apiKeyInput.value.trim();
  if (!provider || !apiKey) {
    alert('Please select a provider and enter an API key.');
    return;
  }
  if (!chrome || !chrome.storage) return; // fallback for local dev
  chrome.storage.sync.set({ provider, apiKey }, () => {
    updateChatInputState();
    alert('Settings saved!');
  });
}

function updateChatInputState() {
  const provider = providerSelect.value;
  const apiKey = apiKeyInput.value.trim();
  const enabled = provider && apiKey;
  userInput.disabled = !enabled;
  chatForm.querySelector('#send-btn').disabled = !enabled;
}

saveSettingsBtn.addEventListener('click', saveSettings);
providerSelect.addEventListener('change', updateChatInputState);
apiKeyInput.addEventListener('input', updateChatInputState);

document.addEventListener('DOMContentLoaded', loadSettings);

function createImportButton(workflowJson, buttonText = 'Import to n8n') {
  const importBtn = document.createElement('button');
  importBtn.textContent = buttonText;
  importBtn.style.marginTop = '8px';
  importBtn.style.padding = '6px 12px';
  importBtn.style.border = '1px solid #ccc';
  importBtn.style.borderRadius = '4px';
  importBtn.style.cursor = 'pointer';

  importBtn.onclick = async () => {
    if (chrome && chrome.tabs) {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0] && tabs[0].id && tabs[0].url && (tabs[0].url.includes('n8n.io') || tabs[0].url.includes('localhost'))) {
          chrome.tabs.sendMessage(
            tabs[0].id,
            { type: 'IMPORT_WORKFLOW_JSON', workflowJson: workflowJson }, // workflowJson is already an object here
            (response) => {
              if (chrome.runtime.lastError) {
                console.error('Error sending message to content script:', chrome.runtime.lastError.message);
                appendMessage(`Error sending to n8n tab: ${chrome.runtime.lastError.message}`, 'bot', {type: 'error'});
                return;
              }
              if (response && response.status === 'ok') {
                appendMessage('Workflow import instruction sent to n8n tab!', 'bot', {type: 'info'});
              } else {
                appendMessage('Failed to send workflow to n8n tab. Ensure you are on an n8n page.', 'bot', {type: 'error'});
              }
            }
          );
        } else {
          appendMessage('No active n8n tab found. Please open your n8n instance and try again.', 'bot', {type: 'error'});
        }
      });
    } else {
      alert('This feature requires the extension to be run in a Chrome environment with an active n8n tab.');
    }
  };
  return importBtn;
}


function appendMessage(text, sender = 'user', metadata = null) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${sender}`;
  const bubble = document.createElement('div');
  bubble.className = `bubble ${sender}`;
  
  // Adjust text content based on metadata type
  if (sender === 'bot' && metadata && metadata.type === 'workflow_json_error_api' && metadata.error_details) {
    bubble.textContent = metadata.error_details; // Show API error as main message
  } else {
    bubble.textContent = text; // Default behavior
  }
  messageDiv.appendChild(bubble);

  if (sender === 'bot' && metadata) {
    if (metadata.type === 'workflow_created' && metadata.n8n_url) {
      // The main text (metadata.reply) is already set by bubble.textContent = text;
      const viewLink = document.createElement('a');
      viewLink.href = metadata.n8n_url;
      viewLink.target = '_blank';
      viewLink.textContent = 'View in n8n';
      viewLink.style.display = 'inline-block';
      viewLink.style.marginLeft = '10px';
      viewLink.style.color = '#2563eb'; // Use consistent link color
      bubble.appendChild(document.createElement('br')); // Add a line break before the link
      bubble.appendChild(viewLink);
    } else if (metadata.type === 'workflow_json_error_api' && metadata.reply) { // metadata.reply is the workflow_json string here
        try {
            const workflowJson = JSON.parse(metadata.reply); // The 'reply' field contains the JSON string
            const detailsBtn = document.createElement('button');
            detailsBtn.textContent = 'View/Import Attempted JSON';
            detailsBtn.style.marginTop = '8px';
            detailsBtn.style.padding = '6px 12px';
            detailsBtn.style.border = '1px solid #ccc';
            detailsBtn.style.borderRadius = '4px';
            detailsBtn.style.cursor = 'pointer';
            
            let detailsVisible = false;
            const detailsContainer = document.createElement('div');
            detailsContainer.style.display = 'none';
            detailsContainer.style.marginTop = '5px';
            
            const preTag = document.createElement('pre');
            preTag.style.backgroundColor = '#f5f5f5';
            preTag.style.padding = '10px';
            preTag.style.borderRadius = '4px';
            preTag.style.maxHeight = '200px';
            preTag.style.overflowY = 'auto';
            preTag.textContent = JSON.stringify(workflowJson, null, 2);
            
            const importButton = createImportButton(workflowJson, 'Import This JSON to n8n');
            
            detailsContainer.appendChild(preTag);
            detailsContainer.appendChild(importButton);
            messageDiv.appendChild(detailsBtn); // Append button to messageDiv, not bubble
            messageDiv.appendChild(detailsContainer);

            detailsBtn.onclick = () => {
                detailsVisible = !detailsVisible;
                detailsContainer.style.display = detailsVisible ? 'block' : 'none';
            };
        } catch (e) {
            console.error("Error parsing workflow_json in workflow_json_error_api:", e);
            // If parsing metadata.reply fails, don't add the button.
        }
    } else if (metadata.type === 'text' && metadata.original_request_type === 'workflow' && metadata.reply && metadata.reply.trim().startsWith('{')) {
        try {
            const json = JSON.parse(metadata.reply);
            const importBtn = createImportButton(json);
            messageDiv.appendChild(importBtn);
        } catch (e) {
            // Not valid JSON, do nothing
        }
    } else if (metadata.type === 'text' && text.trim().startsWith('{') && !metadata.original_request_type) { // Generic JSON case, not explicitly workflow
        try {
            const json = JSON.parse(text);
            const importBtn = createImportButton(json);
            messageDiv.appendChild(importBtn);
        } catch (e) {
            // Not valid JSON, do nothing
        }
    }
  }

  chatWindow.appendChild(messageDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage(message) {
  // Get provider and apiKey from storage
  let provider = providerSelect.value;
  let apiKey = apiKeyInput.value.trim();
  if (chrome && chrome.storage) {
    const data = await new Promise((resolve) => chrome.storage.sync.get(['provider', 'apiKey'], resolve));
    provider = data.provider;
    apiKey = data.apiKey;
  }
  appendMessage(message, 'user');
  userInput.value = '';
  appendMessage('...', 'bot');
  try {
    console.log('Sending message to backend...');
    const res = await fetch('http://localhost:5000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, provider, apiKey })
    });
    const data = await res.json();
    // Remove the '...' loading message
    const loading = chatWindow.querySelector('.message.bot:last-child');
    if (loading && loading.querySelector('.bubble').textContent === '...') {
       chatWindow.removeChild(loading);
    }
    appendMessage(data.reply, 'bot', data); // Pass the full data object as metadata
  } catch (err) {
    console.error('Error sending message or processing response:', err);
    const loading = chatWindow.querySelector('.message.bot:last-child');
    if (loading && loading.querySelector('.bubble').textContent === '...') {
        chatWindow.removeChild(loading);
    }
    appendMessage('Error: Could not reach backend. ' + (err.message || ''), 'bot', {type: 'error'});
  }
}

chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const message = userInput.value.trim();
  if (message) {
    sendMessage(message);
  }
}); 