**Project Title:** Feature Enhancements for GraphHopper Application
**Submitted by:** Alyssa Mae Bacay, Ralph Joseph Berena, Louixiana Mari Calingasan, Jonard Josh Hernandez, Dame Jensen Ona
**Date:** November 2025  
**Instructor/Adviser:** Ms. Elaine Ilao

---

# GraphHopper Route Finder Web App

A Flask-based web application that integrates with the **GraphHopper Geocoding and Routing APIs** to calculate and visualize routes between two locations.  
It supports **car**, **bike**, and **foot** routes, offering both **metric** and **imperial** systems.  
The app includes a modern web interface, interactive map, and detailed travel instructions.

---

## Overview

This project transforms the original console-based routing script into a **fully functional web-based application**.  
It enhances usability through visual feedback, interactive mapping, and modern UI design.

Users can:
- Enter a start and destination location  
- Choose a vehicle type and unit system  
- View total distance and estimated travel time  
- See a visual map of the route with step-by-step instructions  

---

## Features

### Core Functionalities
- Real-time route generation via **GraphHopper API**
- Vehicle support for **Car**, **Bike**, and **Foot**
- Display of total **distance**, **travel time**, and **step-by-step directions**

### Interface & Design
- **Modern and responsive web interface** (HTML, CSS, JavaScript)
- **Interactive Leaflet.js map** for route visualization
- **Scrollable instruction boxes** for easy readability
- Consistent **padding, spacing, and layout**

---

## List of Enhancements and Reasons

| Enhancement | Description | Reason |
|--------------|--------------|---------|
| Web Interface | Converted from console to Flask web app | Improves usability and accessibility |
| Leaflet.js Map | Displays the route visually | Offers clear visual navigation |
| Unit Choice | Toggle between Metric and Imperial systems | User preference and cleaner output |
| Readable Time Format | Displays hours, minutes, seconds | Easier to interpret trip duration |
| Function-Based Structure | Organized code into reusable functions | Easier maintenance and debugging |
| Robust Error Handling | Handles invalid input and API issues | Prevents app crashes and improves reliability |
| Enhanced UI Design | Better padding, spacing, and alignment | Professional and consistent interface |
| Clear Button | Resets inputs, map, and instructions | Improves convenience and workflow |
| Scrollable Instructions | Boxed directions with scroll view | Organized for long route displays |
| Asynchronous Fetch | Uses JavaScript fetch for API calls | Faster and smoother user experience |
| Responsive Design | Adapts to different screens | Usable on mobile and desktop |
| API Key Handling | Centralized in backend | Safer and easier to manage |

---

## Technologies Used

| Category | Technology |
|-----------|-------------|
| **Backend Framework** | Flask (Python) |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Mapping Library** | Leaflet.js |
| **API Provider** | GraphHopper Routing & Geocoding API |
| **Data Format** | JSON |
| **Environment** | Python 3.10+ |

---

## Requirements

To run the application locally, install:

- [Python 3.10+](https://www.python.org/downloads/)
- [Flask](https://pypi.org/project/Flask/)
- [Requests](https://pypi.org/project/requests/)

Install dependencies:
```bash
pip install flask requests
