---
permalink: /
title: ""
excerpt: ""
author_profile: true
redirect_from: 
  - /about/
  - /about.html
---

{% if site.google_scholar_stats_use_cdn %}
{% assign gsDataBaseUrl = "https://cdn.jsdelivr.net/gh/" | append: site.repository | append: "@" %}
{% else %}
{% assign gsDataBaseUrl = "https://raw.githubusercontent.com/" | append: site.repository | append: "/" %}
{% endif %}
{% assign url = gsDataBaseUrl | append: "google-scholar-stats/gs_data_shieldsio.json" %}

<span class='anchor' id='about-me'></span>

# 👋 Welcome!

🎓 I earned a Bachelor of Science degree with First Class Honours from **The Chinese University of Hong Kong** in August 2024. And now, I am engaged in various exciting projects related to **LLM, GNN, and Machine Learning**.

💼 I welcome all opportunities for discussion, learning, and collaboration. If you have any opportunities related to work, study, or collaboration in these areas, please feel free to reach out to me.

# 🔥 News
- *2025.02*: &nbsp;🎉🎉 One paper accepted by <span style="color: darkblue;">**DAC 2025**</span>.
- *2025.01*: &nbsp;🎉🎉 One paper accepted by <span style="color: darkblue;">**ICLR 2025 Spotlight**</span>.
- *2024.12*: &nbsp;🎉🎉 One paper accepted by <span style="color: darkblue;">**Advanced Science**</span>.
- *2024.10*: &nbsp;🎉🎉 Our team's dataset ranked **4th** place among participating teams and won the **Honorable Mention Award** at the **[LLM4HWDesign @ ICCAD 2024](https://nvlabs.github.io/LLM4HWDesign/results.html)**.
- *2024.10*: &nbsp;🎉🎉 One abstract paper has been accepted by **[2025 SPIE Photonics West](https://spie.org/conferences-and-exhibitions/photonics-west#_=_)**.
<!-- - *2024.07*: &nbsp;🎉🎉 I am honored to have been named to the **Dean's List** for the 2023-24 academic year in the Faculty of Engineering at The Chinese University of Hong Kong (CUHK). -->

<!-- # 💬 Invited Talks
- *2021.06*, Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus ornare aliquet ipsum, ac tempus justo dapibus sit amet. 
- *2021.03*, Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus ornare aliquet ipsum, ac tempus justo dapibus sit amet.  \| [\[video\]](https://github.com/) -->


{% include_relative includes/research.md %}

{% include_relative includes/education.md %}

{% include_relative includes/work.md %}