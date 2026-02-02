const logFeed = document.getElementById('log-feed');
const pluginGrid = document.getElementById('plugin-grid');
const cmdInput = document.getElementById('cmd-input');
const pluginSelect = document.getElementById('plugin-select');

async function updateState() {
    // 1. Logs
    try {
        const res = await fetch('/api/logs');
        const logs = await res.json();
        logFeed.innerHTML = logs.map(l =>
            `<div class="log-entry">` +
            `<span class="log-time">[${new Date(l.created_at).toLocaleTimeString()}]</span> ` +
            `<span class="log-status st-${l.status}">${l.status}</span> ` +
            `<b>${l.plugin_id || '?'}</b>: ${l.command_text} ` +
            `${l.error_message ? `<span class="st-ERROR">(${l.error_message})</span>` : ''}` +
            `</div>`
        ).join('');
        // Auto scroll to bottom
        logFeed.scrollTop = logFeed.scrollHeight;
    } catch (e) { }

    // 2. Plugins
    try {
        const res = await fetch('/api/plugins');
        const plugins = await res.json();
        pluginGrid.innerHTML = plugins.map(p =>
            `<div class="feature-card" style="padding: 15px;">` +
            `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">` +
            `<strong>${p.name}</strong>` +
            `<span class="status-badge badge-${p.status === 'running' ? 'running' : 'idle'}">${p.status}</span>` +
            `</div>` +
            `<div style="font-size:0.9em; margin-bottom:5px;">${p.progress || 'Ready'}</div>` +
            `<div style="font-size:0.8em; color:#888;">${p.message || ''}</div>` +
            `</div>`
        ).join('');
    } catch (e) { }
}

document.getElementById('send-btn').onclick = async () => {
    let text = cmdInput.value.trim();
    const prefix = pluginSelect.value;

    // Add prefix if user didn't type a command
    if (prefix && !text.startsWith('/')) {
        text = `${prefix} ${text}`;
    }

    await fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    });
    cmdInput.value = '';
    updateState();
};

document.getElementById('abort-btn').onclick = async () => {
    await fetch('/api/stop', { method: 'POST' });
    alert('Stop Signal Sent');
}

setInterval(updateState, 2000);
updateState();
