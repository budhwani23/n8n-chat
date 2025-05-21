// Listen for messages from the extension
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'IMPORT_WORKFLOW_JSON' && request.workflowJson) {
    // Convert JSON to Blob and create a File
    const jsonStr = JSON.stringify(request.workflowJson, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const file = new File([blob], 'workflow.json', { type: 'application/json' });

    // Create a hidden file input and trigger change event
    const input = document.createElement('input');
    input.type = 'file';
    input.style.display = 'none';
    document.body.appendChild(input);

    // Create a DataTransfer to simulate file selection
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    input.files = dataTransfer.files;

    // Try to find n8n's file input and trigger import
    let found = false;
    const reactInputs = document.querySelectorAll('input[type="file"]');
    for (const reactInput of reactInputs) {
      if (reactInput && reactInput.accept && reactInput.accept.includes('application/json')) {
        reactInput.files = dataTransfer.files;
        reactInput.dispatchEvent(new Event('change', { bubbles: true }));
        found = true;
        break;
      }
    }

    // Fallback: trigger the import menu if not found
    if (!found) {
      const menuBtn = document.querySelector('svg[data-icon="ellipsis-h"], .fa-ellipsis-h');
      if (menuBtn && menuBtn.parentElement) menuBtn.parentElement.click();
      setTimeout(() => {
        const importBtn = Array.from(document.querySelectorAll('div')).find(
          el => el.textContent && el.textContent.includes('Import from File')
        );
        if (importBtn) importBtn.click();
        setTimeout(() => {
          const reactInputs2 = document.querySelectorAll('input[type="file"]');
          for (const reactInput of reactInputs2) {
            if (reactInput && reactInput.accept && reactInput.accept.includes('application/json')) {
              reactInput.files = dataTransfer.files;
              reactInput.dispatchEvent(new Event('change', { bubbles: true }));
              break;
            }
          }
        }, 500);
      }, 500);
    }

    // Show a notification
    const note = document.createElement('div');
    note.textContent = 'n8n-chat: Workflow imported!';
    note.style.position = 'fixed';
    note.style.top = '20px';
    note.style.right = '20px';
    note.style.background = '#4f8cff';
    note.style.color = '#fff';
    note.style.padding = '12px 18px';
    note.style.borderRadius = '8px';
    note.style.zIndex = 99999;
    note.style.fontSize = '16px';
    document.body.appendChild(note);
    setTimeout(() => note.remove(), 3000);

    sendResponse({ status: 'ok' });
  }
}); 