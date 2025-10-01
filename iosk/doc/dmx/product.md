# About the Product

## Overall Purpose

Diametrix FAS is a **Financial Analysis System (FAS)** used for analyzing financial data in the context of loan applications. The core functionality involves extracting data from various document types (tax returns, bank statements, etc.) and using this data to generate reports and make assessments.

## Core Modules

Diametrix FAS offers spreading for loans focused around three types of entities:

*   **Individual:** Consumer loans and loan guarantor analysis.
*   **Business:** Commercial & industrial loans.
*   **Agriculture:** Farm and agriculture loans.

### Pro Features

The "Pro" plan includes a number of additional features not found in the basic product. Additional "Pro" features include:

*   Integration with additional systems such as property tax databases.
*   Additional loan analysis and verification checks.

## Key Technologies

*   **Backend:**
    *   **Python:** The backend is primarily written in Python.
    *   **Websockets:** Uses websockets communication with the frontend.
    *   **Google Document AI:** Integrates with Google's Document AI service for document processing, specifically to extract data from financial documents.
    *   **Database (SQLite):** Utilizes SQLite for data storage, including application data, user information, policy rules, and document contents. Currently SQLite (temporarily) but should probably be PostgreSQL for production.
*   **Frontend:**
    *   **Svelte:** The frontend is built using Svelte, a JavaScript compiler that produces highly optimized web applications.

## Key Functionalities

*   **User Authentication and Authorization:** User management and role-based access control.
*   **Policy Enforcement:** A system for enforcing rules and constraints on the data and processes.
*   **Document Processing and Data Extraction:** The project heavily relies on Google Document AI to extract information from documents. The extracted data is then used to populate data models within the application.
*   **Data Validation and Reporting:** Document staging and issue tracking mechanisms for data quality and reporting.
*   **Websocket Communication:** The backend is built using websockets, and `diametrix.js` in the frontend manages the communication.
*   **Data Presentation:** Svelte components are used to display data in a structured manner (e.g., tables) for analysis.

## Conclusion

In summary, Diametrix FAS is a sophisticated application for automating financial analysis and spreading, leveraging modern web technologies and cloud-based document processing.

