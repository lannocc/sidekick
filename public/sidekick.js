/*
 * Copyright (C) 2025 LANNOCC
 * @%@~LICENSE~@%@
 */

/* SEE ALSO: /sk/web.py */
const VERSION = 1;
const PREAMBLE = '::SKAI:' + VERSION + '::';
const PREAMBLE_UPLOAD = '::SKAIUP:' + VERSION + '::';
const PREAMBLE_UPLOAD_ASYNC = '::SKAIGOUP:' + VERSION + '::';
const PORT = 40642

const WAIT_RECONNECT = 981; // milliseconds

let status_text = '';
let status_class = '';

let sws = null; // sidekick websocket
let connecting = true;
let on_message = new Map();

let _sess_token_ = null;

const proto = window.location.protocol == 'https:' ? 'wss:' : 'ws:';
const WEBSOCKET_URL = proto+'//'+window.location.hostname + (
    window.location.protocol != 'https:' ? (':'+PORT) : '');
console.log(WEBSOCKET_URL);

function sws_connect() {
    status_text = 'BACK-END START-UP';
    status_class = 'connecting';
    const status = document.getElementById('status_img');
    if (status) {
        status.title = 'FAS ' + status_text;
        status.className = status_class;
    }

    sws = new WebSocket(WEBSOCKET_URL);

    sws.addEventListener('open', (event) => {
        status_text = 'READY';
        status_class = 'online';
        const status = document.getElementById('status_img');
        if (status) {
            status.title = 'FAS ' + status_text;
            status.className = status_class;
        }
        connecting = false;
    });

    sws.addEventListener('close', async (event) => {
        console.error(event);
        if (connecting) {
            status_text = 'WAIT FOR ' + status_text;
            status_class = 'error';
        }
        else {
            status_text = 'CLOSED';
            status_class = '';
        }

        const status = document.getElementById('status_img');
        if (status) {
            status.title = 'FAS ' + status_text;
            status.className = status_class;
        }

        connecting = true;
        setTimeout(() => {
            status_text = 'RETRYING';
            status_class = 'retrying';
            if (status) {
                status.title = 'FAS ' + status_text;
                status.className = status_class;
            }
            setTimeout(sws_connect, WAIT_RECONNECT / 2);
        }, WAIT_RECONNECT / 2);
    });

    sws.addEventListener('message', async (event) => {
        if (!on_message.size) {
            console.log('ignoring', event);
            return;
        }

        const sorted = new Map([...on_message].sort((a, b) => a[0] - b[0]));
        let common = false;
        if (sorted.has(0)) {
            common = sorted.get(0);
            sorted.delete(0);
        }

        const data = JSON.parse(event.data);
        let done = false;

        for (const [ slot, callback ] of sorted.entries()) {
            done = await callback(data);
            if (done) break;
        }

        if (!done && common) {
            await common(data);
        }
    });
}

async function sws_send(data) {
    const msg = PREAMBLE + JSON.stringify(data);

    if (connecting) {
        async function waitForConnect() {
            function waitForIt() {
                if (! connecting) return;
                return new Promise((resolve) => setTimeout(resolve, 100))
                    .then(() => Promise.resolve())
                    .then(() => waitForIt());
            }
            return waitForIt();
        }

        await waitForConnect();
    }

    sws.send(msg);
}

async function sws_upload(data) {
    const msg = PREAMBLE_UPLOAD + data;

    if (connecting) {
        async function waitForConnect() {
            function waitForIt() {
                if (! connecting) return;
                return new Promise((resolve) => setTimeout(resolve, 100))
                    .then(() => Promise.resolve())
                    .then(() => waitForIt());
            }
            return waitForIt();
        }

        await waitForConnect();
    }

    sws.send(msg);
}

window.sk_on_message = (callback, slot) => {
    if (slot) {
        if (!Number.isInteger(slot)) {
            console.error('slot must be integer', slot);
            return;
        }
    }
    else slot = 0;
    on_message.set(slot, callback);
}

window.sk_status = () => {
    return [ status_text, status_class ];
};

window.sk_reset = (reason) => {
    if (reason) sws.close(4209, reason);
    else sws.close();
};

window.sk_call = async (fn, data) => {
    if (data === undefined) data = { };
    req = { };
    req[fn] = data;
    req['sess_token'] = _sess_token_;
    return sws_send(req);
};

window.sk_upload = async (cmd, args, data) => {
    return sws_upload(`${cmd}:${args}$` + data);
};


BigInt.prototype.toJSON = function () {
    return this.toString();
}

/*
window.money = function(val) {
    if (val === undefined || val === null) {
        return '***';
    }

    if (typeof val == 'object') {
        if (Object.hasOwn(val, 'number')) {
            val = val.number;
        }
        else {
            for (const v in val) { // data array of references (FIXME)
                val = parseFloat(v);
                break; // should only be one
            }
        }
    }

    if (val === undefined || val === null) {
        return '***';
    }

    //return '$' + val.toFixed(2);
    return '$' + val.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
};

window.percent = function(val) {
    if (val === undefined || val === null) {
        return '***';
    }

    if (typeof val == 'object' && Object.hasOwn(val, 'number')) {
        val = val.number;
    }

    //return '' + (val*100).toFixed(2) + '%';
    return '' + (val*100).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }) + '%';
};
*/


sws_connect(); // connect automatically on script (page) load

