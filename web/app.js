// Frontend Application Logic for Smart Travel Planner AI Agent

document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const thinkingIndicator = document.getElementById("agent-thinking");
    const noTripPlaceholder = document.getElementById("no-trip-placeholder");
    const tripDashboard = document.getElementById("trip-dashboard");

    // Dashboard Elements
    const dashDest = document.getElementById("dash-destination");
    const dashDuration = document.getElementById("dash-duration");
    const dashTravelers = document.getElementById("dash-travelers");
    const dashOrigin = document.getElementById("dash-origin");
    const dashWeather = document.getElementById("dash-weather");
    const dashStatus = document.getElementById("dash-budget-status");
    const dashTotal = document.getElementById("dash-total-budget");
    const dashPerPerson = document.getElementById("dash-per-person");
    const dashTarget = document.getElementById("dash-target-budget");

    const costStay = document.getElementById("cost-stay");
    const costFood = document.getElementById("cost-food");
    const costCommute = document.getElementById("cost-commute");
    const costActivities = document.getElementById("cost-activities");
    const costBuffer = document.getElementById("cost-buffer");

    const daysContainer = document.getElementById("days-container");
    const tipsList = document.getElementById("tips-list");

    // Initial load: check if an active trip exists in memory
    fetchActiveTrip();

    // Handle Form Submit
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        appendMessage("user", message);
        userInput.value = "";
        showThinking(true);

        try {
            const resp = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message })
            });
            const data = await resp.json();
            handleAgentResponse(data);
        } catch (err) {
            appendMessage("agent", "Error: Failed to connect to server. Please try again.");
        } finally {
            showThinking(false);
        }
    });

    // Quick Prompt Pills
    document.querySelectorAll(".pill").forEach(pill => {
        pill.addEventListener("click", () => {
            const promptText = pill.getAttribute("data-prompt");
            userInput.value = promptText;
            chatForm.dispatchEvent(new Event("submit"));
        });
    });

    // Top Header Buttons
    document.getElementById("btn-compare-budget").addEventListener("click", () => {
        userInput.value = "compare budget packages";
        chatForm.dispatchEvent(new Event("submit"));
    });

    document.getElementById("btn-export-html").addEventListener("click", () => {
        window.open("/api/export?format=html", "_blank");
    });

    document.getElementById("btn-reset").addEventListener("click", async () => {
        if (confirm("Reset current trip plan and session?")) {
            await fetch("/api/reset", { method: "POST" });
            chatMessages.innerHTML = `
                <div class="message agent-msg">
                    <div class="msg-avatar">🤖</div>
                    <div class="msg-content">
                        <p><strong>Session reset.</strong> Where would you like to plan your next trip?</p>
                    </div>
                </div>
            `;
            noTripPlaceholder.classList.remove("hidden");
            tripDashboard.classList.add("hidden");
        }
    });

    function showThinking(show) {
        if (show) {
            thinkingIndicator.classList.remove("hidden");
        } else {
            thinkingIndicator.classList.add("hidden");
        }
    }

    function appendMessage(sender, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender}-msg`;
        const avatar = sender === "user" ? "👤" : "🤖";

        // Convert linebreaks to paragraphs/breaks
        const formattedText = text.replace(/\n/g, "<br>");
        msgDiv.innerHTML = `
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-content">${formattedText}</div>
        `;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function handleAgentResponse(res) {
        const type = res.type;

        if (type === "CLARIFICATION_REQUIRED") {
            appendMessage("agent", `<strong>Clarification:</strong> ${res.question}`);
        } else if (type === "TRIP_GENERATED") {
            appendMessage("agent", `✨ I have generated a complete itinerary for <strong>${res.trip_plan.destination}</strong>! Take a look at the dashboard on the right.`);
            renderDashboard(res.trip_plan);
        } else if (type === "PLAN_UPDATED") {
            appendMessage("agent", `✅ <strong>Itinerary Updated:</strong><br>${res.summary}`);
            renderDashboard(res.trip_plan);
        } else if (type === "DESTINATION_RECOMMENDATIONS" || type === "BUDGET_COMPARISON") {
            appendMessage("agent", res.content);
        } else if (type === "TRIP_EXPORTED") {
            appendMessage("agent", `📁 ${res.content}<br><a href="/api/export?format=html" target="_blank" style="color:#2563eb; font-weight:bold;">Click here to view / print HTML itinerary</a>`);
        } else {
            appendMessage("agent", res.content || "Ready to assist with your travel planning!");
        }
    }

    async function fetchActiveTrip() {
        try {
            const resp = await fetch("/api/trip");
            if (resp.ok) {
                const plan = await resp.json();
                if (plan && plan.destination) {
                    renderDashboard(plan);
                }
            }
        } catch (e) {
            // No active trip yet
        }
    }

    function renderDashboard(plan) {
        noTripPlaceholder.classList.add("hidden");
        tripDashboard.classList.remove("hidden");

        dashDest.textContent = `${plan.destination}`;
        dashDuration.textContent = `${plan.duration_days} Days`;
        dashTravelers.textContent = `${plan.travelers_count} Traveler(s)`;
        dashOrigin.textContent = plan.origin ? `From ${plan.origin}` : "Origin: N/A";

        // Budget
        const b = plan.budget;
        dashTotal.textContent = `₹${b.total_estimated.toLocaleString()}`;
        dashPerPerson.textContent = `₹${b.per_person_estimated.toLocaleString()}`;
        dashTarget.textContent = b.target_budget ? `₹${b.target_budget.toLocaleString()}` : "Not specified";

        if (b.is_over_budget) {
            dashStatus.className = "status-badge status-over";
            dashStatus.textContent = "⚠️ Over Budget";
        } else {
            dashStatus.className = "status-badge status-ok";
            dashStatus.textContent = "✅ Within Budget";
        }

        costStay.textContent = `₹${b.accommodation_cost.toLocaleString()}`;
        costFood.textContent = `₹${b.food_cost.toLocaleString()}`;
        costCommute.textContent = `₹${b.transport_cost.toLocaleString()}`;
        costActivities.textContent = `₹${b.activities_cost.toLocaleString()}`;
        costBuffer.textContent = `₹${b.contingency_cost.toLocaleString()}`;

        // Weather check in travel_tips
        const weatherTip = plan.travel_tips.find(t => t.toLowerCase().includes("weather"));
        if (weatherTip) {
            const tempMatch = weatherTip.match(/(\d+\.?\d*)°C/);
            dashWeather.querySelector(".weather-temp").textContent = tempMatch ? `${tempMatch[1]}°C` : "24°C";
            dashWeather.querySelector(".weather-cond").textContent = weatherTip.split(".")[0];
        }

        // Days
        daysContainer.innerHTML = "";
        plan.days.forEach(day => {
            const dayCard = document.createElement("div");
            dayCard.className = "day-card";

            const actsHtml = day.activities.map(act => `
                <div class="activity-item">
                    <div class="activity-header">
                        <span>${act.time_slot}: ${act.title}</span>
                        <span>₹${act.estimated_cost}</span>
                    </div>
                    <div class="activity-desc">${act.description}</div>
                    <div class="activity-meta">
                        ${act.opening_hours ? `Hours: ${act.opening_hours} &bull; ` : ""}
                        Duration: ~${act.duration_hours} hrs
                        ${act.source_url ? `&bull; <a href="${act.source_url}" target="_blank" style="color:#2563eb;">Source</a>` : ""}
                    </div>
                </div>
            `).join("");

            dayCard.innerHTML = `
                <div class="day-title">
                    <span>Day ${day.day_number}: ${day.theme}</span>
                    <span style="font-size:0.85rem; color:#64748b;">Est. Day Cost: ₹${day.estimated_day_cost}</span>
                </div>
                ${actsHtml}
                ${day.transit_notes ? `<div class="day-transit-note">🚗 ${day.transit_notes}</div>` : ""}
            `;
            daysContainer.appendChild(dayCard);
        });

        // Tips List
        tipsList.innerHTML = "";
        plan.travel_tips.forEach(tip => {
            const li = document.createElement("li");
            li.textContent = tip;
            tipsList.appendChild(li);
        });
        plan.safety_advisories.forEach(safe => {
            const li = document.createElement("li");
            li.innerHTML = `<strong>⚠️ Advisory:</strong> ${safe}`;
            tipsList.appendChild(li);
        });
    }
});
