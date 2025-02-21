---
name: Bug report
about: Create a report to help us improve
title: " "
labels: ''
assignees: ''

---

name: Service Request
description: Create a new ticket for service requests.
title: "[TICKET] - "
labels: ["ticket"]
body:
  - type: dropdown
    id: priority
    attributes:
      label: "Priority"
      options:
        - P1
        - P2
        - P3
        - P4
  - type: input
    id: assignee
    attributes:
      label: "Assigned To (GitHub Username)"
  - type: textarea
    id: description
    attributes:
      label: "Description"
