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

function appendMessage(text, sender = 'user') {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${sender}`;
  const bubble = document.createElement('div');
  bubble.className = `bubble ${sender}`;
  bubble.textContent = text;
  messageDiv.appendChild(bubble);

  // If bot and looks like JSON, add import button
  if (sender === 'bot' && text.trim().startsWith('{')) {
    try {
      const json = JSON.parse(text);
      const importBtn = document.createElement('button');
      importBtn.textContent = 'Import to n8n';
      importBtn.style.marginTop = '8px';
      importBtn.onclick = async () => {
        // Get the active tab
        if (chrome && chrome.tabs) {
          chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0] && tabs[0].id) {
              chrome.tabs.sendMessage(
                tabs[0].id,
                { type: 'IMPORT_WORKFLOW_JSON', workflowJson: json },
                (response) => {
                  if (response && response.status === 'ok') {
                    appendMessage('Workflow sent to n8n for import!', 'bot');
                  } else {
                    appendMessage('Failed to send workflow to n8n.', 'bot');
                  }
                }
              );
            } else {
              appendMessage('No active n8n tab found.', 'bot');
            }
          });
        }
      };
      messageDiv.appendChild(importBtn);
    } catch (e) {
      // Not valid JSON, do nothing
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
    if (loading && loading.textContent === '...') chatWindow.removeChild(loading);
    appendMessage(data.reply, 'bot');
  } catch (err) {
    const loading = chatWindow.querySelector('.message.bot:last-child');
    if (loading && loading.textContent === '...') chatWindow.removeChild(loading);
    appendMessage('Error: Could not reach backend.', 'bot');
  }
}

chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const message = userInput.value.trim();
  if (message) {
    sendMessage(message);
  }
}); 