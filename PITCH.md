# RoadSense — 3-Minute Pitch

---

## [0:00–0:30] The Hook

> Open Google Maps right now. Search for any route in Bangalore.

> It'll tell you it's 7 km, 25 minutes, moderate traffic. What it *won't* tell you is that there are **14 unmarked speed breakers** on that stretch, a **crater** the size of a dining table near KR Puram junction, and the **last 500 meters turned to gravel** after yesterday's rain.

> There's a massive gap between what maps *know* and what roads *are*. Google Maps sees the world from satellites and traffic pings. **It has never actually driven your route.**

> We built something that has.

---

## [0:30–1:00] The Problem

> Today, the only way road hazards get reported is **manual user reports** — someone pulls over on Waze or Google Maps and types "pothole here." The problem? **Almost nobody does it.** You're dodging autos, braking for pedestrians, navigating chaos — and someone expects you to stop and file a report?

> The result: a **perpetually incomplete, permanently stale** picture of actual road conditions. Potholes go unreported for months. Speed breakers don't exist on any map. Entire stretches of dangerous road are invisible to navigation.

> And this isn't a minor inconvenience — India loses over **1.7 lakh lives to road accidents every year.** Road surface conditions are a direct contributor, and we're flying blind.

---

## [1:00–1:45] The Solution — RoadSense

> **RoadSense turns every dashcam drive into an automatic road survey — zero driver effort.**

> Here's how it works. You drive with a GoPro mounted on your dashboard. That's it. That's all you do.

> Behind the scenes: we extract the GPS telemetry embedded in the GoPro footage, chunk the video into segments, and feed each one through **Gemini 2.5 Pro's multimodal analysis**. Gemini doesn't just detect potholes — it understands *context*. It sees a festival procession blocking a lane, an auto-rickshaw reversing into traffic, a waterlogged patch after a drainage overflow. The **long tail of Indian road hazards is infinite** — and Gemini handles novel situations without retraining.

> Every detection comes back as structured data: **what** the hazard is, **how severe** it is, **where** it is on GPS, and critically — **what the driver should do about it.** *"Pothole ahead, severity 4, steer right to avoid."*

> We deduplicate across video segments, map everything to GPS coordinates, and render it on a **split-screen interface** — annotated dashcam video on one side, severity-coded hazard zones on Google Maps on the other, with **voice alerts** that guide you through the route.

> *(Live demo: show before/after — raw chaotic Bangalore footage vs. the same route through RoadSense with bounding boxes, map markers, voice alerts, and route summary card)*

> *"This 4 km route: 12 hazards detected, road quality 5 out of 10, worst segment near Tin Factory junction."*

---

## [1:45–2:20] The Vision — Collective Road Intelligence

> One dashcam is useful. **A thousand dashcams is a revolution.**

> The real vision is **collective road intelligence**. Partner with cab fleets — Ola, Uber, logistics companies. Thousands of vehicles already driving every route, every day. Each one becomes a **passive road sensor** feeding into a living, breathing hazard map.

> Add **temporal intelligence**: a pothole reported three months ago but not confirmed by recent drivers? Confidence drops. One confirmed by five drivers this week? It gets flagged as critical. The map **stays fresh** because it's continuously validated by real-world observations.

> Then give drivers something they've never had: a **"smoothest route" option**. Not just fastest, not just shortest — **least hazardous.** Before you even start driving, you see road quality scores for every route, personalized to your vehicle type. A sedan cares about potholes differently than an SUV.

> On the cost side — we start with Gemini for its unmatched contextual reasoning, then **distill** into specialized lightweight models for each hazard type. Cloud cost drops from dollars per drive to **pennies per kilometer**. Deploy on-device, and you get **true real-time alerts** without uploading a single frame.

---

## [2:20–2:50] Why This Wins

> Three things make this different:

> **One — passive collection.** Every other solution requires someone to actively report. We flip that. You just drive. The data collects itself. That's not an incremental improvement — it's a **fundamentally different data collection model** that scales to millions of kilometers per day.

> **Two — Gemini's contextual reasoning.** A YOLO model sees "object in road." Gemini sees "unmarked speed breaker with faded paint, approach at 20 kmph, common near school zones." That **contextual understanding** is what turns raw detection into actionable driver guidance.

> **Three — the network effect.** Every driver who uses RoadSense makes the map better for every other driver. More cars, more observations, more confidence, fresher data. **The product gets better the more people use it — without anyone doing anything extra.**

---

## [2:50–3:00] The Close

> Google Maps solved *where to go.* Waze solved *when to go.*

> **RoadSense solves *what you'll actually face when you get there.***

> We're bridging the last gap in navigation — the gap between the map and the road. And we're doing it with the technology that finally makes it possible: Gemini's multimodal intelligence.

> **One dashcam today. Collective road intelligence tomorrow.**

> Thank you.

---

*RoadSense — Gemini 2.5 Hackathon, Bengaluru*
