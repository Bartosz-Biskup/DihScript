const FIX_URL = "https://105d-2001-1b81-11e9-1200-c10f-83bd-1505-27a.ngrok-free.app/fix";
const REGISTER_SUBSCRIBER_URL = "https://105d-2001-1b81-11e9-1200-c10f-83bd-1505-27a.ngrok-free.app/subscriber"


async function fixScript(mode, 
    script, 
    length, 
    target_audience, 
    call_to_action,
    email) {
        const payload = {
            "mode": mode,
            "script": script,
            "length": Number(length),
            "target_audience": target_audience,
            "call_to_action": call_to_action,
            "email": email
        };

        const response = await fetch(
            FIX_URL,
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload)
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(`HTTP: ${response.status}, detail: ${data.detail}`)
        };

        return data;
    }


async function registerSubscriber(name, email) {
    const payload = {
        "name": name,
        "email": email
    };

    const response = await fetch(
        REGISTER_SUBSCRIBER_URL,
        {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        }
    );

    if (!response.ok) {
        throw new Error(`HTTP: ${response.status}`)
    };
}


async function runFixScript() {
    const errorText = document.querySelector("#result-error-text");
    const errorCard = document.querySelector("#result-error");

    errorCard.hidden = true;

    const data_ = new FormData(form);

    const email = data_.get("email");
    const name = data_.get("name")

    const mode = data_.get("mode");
    const script = data_.get("script");
    const length = data_.get("length");
    const targetAudience = data_.get("target_audience");
    const callToAction = data_.get("call_to_action");

    if (mode === "sell") {
        if (!targetAudience) {
            const audienceInput = document.querySelector("#field-audience");

            audienceInput.setCustomValidity("Target audience is required in sell mode");
            audienceInput.reportValidity();
            return;
        }

        if (!callToAction) {
            const ctaInput = document.querySelector("#field-cta");

            ctaInput.setCustomValidity("Call to action is required in sell mode");
            ctaInput.reportValidity();
            return;
        }
    };

    if (!localStorage.getItem("name") || !localStorage.getItem("email")) {
        await registerSubscriber(name, email);

        localStorage.setItem("email", email);
        localStorage.setItem("name", name);
    };

    const submitButton = document.querySelector("#submit-button"); 
    const resultsSection = document.querySelector("#results"); 

    submitButton.classList.add("is-loading");
    resultsSection.classList.add("is-loading");
    submitButton.disabled = true;

    let data;
    try {
        data = await fixScript(mode, script, length, targetAudience, callToAction, email);
    } catch (error) {
        errorText.textContent = `Error: ${error}`;
        errorCard.hidden = false;
        return;
    } finally {
        submitButton.classList.remove("is-loading");
        resultsSection.classList.remove("is-loading");
        submitButton.disabled = false;
    }

    if (data.error) {
        errorText.textContent = `Error: ${data.error}`;
        errorCard.hidden = false;
    } else {
        const resultScript = document.querySelector("#result-script");      
        const resultInfo = document.querySelector("#result-info");       
        const resultChanges = document.querySelector("#result-changes");       
        const resultChangesCount = document.querySelector("#result-changes-count"); 
        const resultLengthBadge = document.querySelector("#result-length-badge");   
        
        resultScript.textContent = data.script;
        resultInfo.textContent = data.info;
        resultChangesCount.textContent = data.changes.length;
        resultLengthBadge.textContent = `${length} sec`;

        resultChanges.replaceChildren();

        if (data.changes.length === 0) {
            const empty = document.createElement("li");
            empty.className = "changes-list__empty placeholder";
            empty.textContent = "No changes needed - The script was already solid✅";
            resultChanges.append(empty);
        }

        for (const change of data.changes) {
            const li = document.createElement("li");
            li.className = "change";

            const reasonEl = document.createElement("p");
            reasonEl.className = "change__reason";
            reasonEl.textContent = change.reason;

            const rangeEl = document.createElement("p");
            rangeEl.className = "change__range";
            rangeEl.textContent = `[${change.start_char} - ${change.end_char}]`;

            li.append(reasonEl, rangeEl);
            resultChanges.append(li);
        }
    }
}


const form = document.querySelector("#fix-form");
const ctaField = document.querySelector("#field-cta");
const audienceField = document.querySelector("#field-audience");


form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await runFixScript();
});

ctaField.addEventListener("input", () => {
    ctaField.setCustomValidity("");
});

audienceField.addEventListener("input", () => {
    audienceField.setCustomValidity("");
});
