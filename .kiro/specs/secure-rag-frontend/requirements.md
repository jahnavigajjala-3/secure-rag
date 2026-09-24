# Requirements Document

## Introduction

SecureRAG is a secure enterprise document intelligence platform. This spec covers the complete replacement of the existing frontend with a proper enterprise application flow. The current frontend lacks a landing page, exposes internal technical details to users, uses a hardcoded role-toggle instead of backend-driven authorization, and does not implement the full product specification (missing landing page, audit logs, settings, employee detail, proper drag-and-drop upload, and My Documents).

The new frontend implements the full user journey:

**Landing Page → Login / Sign Up → Authentication → Backend resolves role → Admin Dashboard OR Employee Dashboard**

The frontend is built with React, TypeScript, Vite, Tailwind CSS, shadcn/ui component patterns, React Router, and TanStack Query. It uses mock data so it can be tested fully before backend integration. All API calls are isolated in a single layer for easy future wiring.

## Glossary

- **System**: The SecureRAG Frontend application
- **Admin**: An authenticated user whose role is resolved as "admin" by the backend
- **Employee**: An authenticated user whose role is resolved as anything other than "admin" by the backend
- **Auth_Service**: The frontend authentication context that reads role information from the backend JWT response
- **Router**: The React Router instance managing all page navigation
- **API_Client**: The isolated module containing all backend fetch calls
- **Mock_Layer**: The mock data module used in place of live API calls during development
- **Landing_Page**: The public marketing page shown before authentication
- **Admin_Dashboard**: The main page shown to authenticated Admin users
- **Employee_Dashboard**: The main page shown to authenticated Employee users
- **Ask_AI**: The RAG chat interface available to authenticated Employees
- **My_Documents**: The document list filtered to only documents accessible by the authenticated Employee
- **Document_Upload**: The drag-and-drop file upload component used by Admins
- **Audit_Log**: A record of administrative actions visible only to Admins

---

## Requirements

### Requirement 1: Landing Page

**User Story:** As a visitor, I want to see a polished marketing introduction page, so that I understand what SecureRAG does before deciding to sign in or get started.

#### Acceptance Criteria

1. THE System SHALL display a landing page at the root path "/" that is accessible without authentication.
2. THE Landing_Page SHALL display the SecureRAG name and a shield-style logo or icon.
3. THE Landing_Page SHALL display a short product tagline of no more than 15 words that communicates enterprise document intelligence.
4. THE Landing_Page SHALL explain SecureRAG's purpose using complete sentences, no acronyms, and no terms that require prior knowledge of information-retrieval technology.
5. WHEN a visitor clicks "Get Started", THE Router SHALL navigate to "/register".
6. WHEN a visitor clicks "Sign In", THE Router SHALL navigate to "/login".
7. THE Landing_Page SHALL display exactly three feature highlights in this order: "Role-Based Access", "Secure Document Retrieval", and "AI-Powered Knowledge Search".
8. THE Landing_Page SHALL NOT display any chat interface, document list, or application UI.
9. THE Landing_Page SHALL NOT use any of the following terms in any visible text: "vector indexing", "RBAC Pre-Filtered", "Security-Bounded QA", "ChromaDB", "MiniLM", "distance threshold", "vector", "RBAC", "embedding".
10. IF a user is already authenticated, THEN THE Router SHALL redirect them from "/" to their role-appropriate dashboard ("/admin/dashboard" for admins, "/employee/dashboard" for employees).

### Requirement 2: Authentication — Login

**User Story:** As a registered user, I want to sign in with my email and password, so that I can access my authorized workspace.

#### Acceptance Criteria

1. THE System SHALL provide a login page at the path "/login" containing an email input field, a password input field, and a submit button.
2. WHEN a user submits valid credentials, THE Auth_Service SHALL store the JWT access token in the browser's local storage and redirect the user based on their backend-resolved role.
3. IF the backend-resolved role is "admin", THEN THE Router SHALL redirect the authenticated user to "/admin/dashboard".
4. IF the backend-resolved role is anything other than "admin", THEN THE Router SHALL redirect the authenticated user to "/employee/dashboard".
5. IF the backend returns a 401 response, THEN THE System SHALL display an error message stating that the email or password is incorrect.
6. IF a network error occurs during login, THEN THE System SHALL display an error message that does not contain stack traces, endpoint URLs, or internal error codes.
7. WHILE the authentication request is in progress, THE System SHALL display a loading indicator and disable the submit button to prevent duplicate submissions.
8. THE System SHALL NOT redirect to a role-selection screen after login; the backend determines the user's role.
9. IF the user attempts to submit the login form with an empty email or empty password field, THEN THE System SHALL display an inline validation error and SHALL NOT submit the request to the backend.

### Requirement 3: Authentication — Sign Up

**User Story:** As a new user, I want to register an account with my name, email, and password, so that my organization administrator can then grant me access.

#### Acceptance Criteria

1. THE System SHALL provide a sign-up page at "/register" accessible from the landing page "Get Started" button and from the login page.
2. THE Sign_Up_Form SHALL collect: full name, email address, password, and password confirmation.
3. THE Sign_Up_Form SHALL NOT include any field or selector that allows the user to choose "Admin" or "Employee" as their account type.
4. IF the user attempts to submit the form and the password and password confirmation do not match, THEN THE System SHALL display an inline validation error and SHALL NOT submit the request to the backend.
5. IF the user attempts to submit the form and the password is fewer than 6 characters or more than 128 characters, THEN THE System SHALL display an inline validation error and SHALL NOT submit the request to the backend.
6. WHEN registration succeeds, THE System SHALL display a success message confirming account creation.
7. WHEN the success message is displayed, THE Router SHALL navigate the user to "/login".
8. IF the backend returns a 409 conflict response, THEN THE System SHALL display a message stating that an account with this email already exists.
9. IF the user attempts to submit the form with an email address that does not match the format local@domain.tld, THEN THE System SHALL display an inline validation error and SHALL NOT submit the request to the backend.
10. IF the backend returns a non-409 error response, THEN THE System SHALL display a generic error message instructing the user to try again, without exposing internal error details.
11. WHILE the registration request is in progress, THE System SHALL display a loading indicator and disable the submit button.

### Requirement 4: Protected Routing and Role-Based Navigation

**User Story:** As the system, I want to restrict page access based on the authenticated user's backend-resolved role, so that employees cannot access admin pages and unauthenticated users cannot access any protected pages.

#### Acceptance Criteria

1. IF a user who is not authenticated attempts to access any path other than "/", "/login", or "/register", THEN THE Router SHALL redirect them to "/login".
2. IF a user authenticated as an Admin attempts to access any path under "/admin/*", THEN THE Router SHALL allow access.
3. IF a user authenticated as an Employee attempts to access any path under "/admin/*", THEN THE Router SHALL redirect them to "/employee/dashboard".
4. IF a user authenticated as an Employee attempts to access any path under "/employee/*", THEN THE Router SHALL allow access.
5. IF a user authenticated as an Admin attempts to access any path under "/employee/*", THEN THE Router SHALL redirect them to "/admin/dashboard".
6. THE System SHALL determine the user's role exclusively from the Auth_Service, which reads the role from the backend JWT response payload.
7. THE System SHALL NOT provide any client-side mechanism (button, toggle, dropdown, or form field) that allows a user to change or select their role.
8. WHEN the Auth_Service detects that the stored token has expired (by checking the token's exp claim), THE Auth_Service SHALL remove the token from local storage and redirect the user to "/login".
9. IF the Auth_Service is unavailable or fails to parse the stored token, THEN THE System SHALL treat the user as unauthenticated and redirect to "/login".
10. IF an authenticated user accesses the root path "/", THEN THE Router SHALL redirect them to their role-appropriate dashboard.

### Requirement 5: Admin Navigation

**User Story:** As an Admin, I want a clear navigation sidebar with access to all admin sections, so that I can manage the platform efficiently.

#### Acceptance Criteria

1. WHILE a user is authenticated as an Admin, THE System SHALL display a sidebar containing navigation links in this order: Dashboard, Employees, Roles, Documents, Audit Logs, Settings.
2. WHILE a user is authenticated as an Admin, THE Admin sidebar SHALL display the user's full name if available, or their email address as a fallback, together with a label identifying their role as "Admin".
3. WHILE a user is authenticated as an Admin, THE Admin sidebar SHALL include a sign-out action that, when activated, terminates the session, removes the stored token, and navigates to "/login".
4. WHILE a user is authenticated as an Admin, THE Admin sidebar SHALL NOT display navigation items including "Ask AI" or "My Documents".
5. WHILE a user is authenticated as an Admin, THE Admin sidebar SHALL visually distinguish the currently active navigation link from inactive links.

### Requirement 6: Admin Dashboard

**User Story:** As an Admin, I want a dashboard showing key platform metrics and recent activity, so that I can monitor the state of the organization's knowledge platform.

#### Acceptance Criteria

1. THE Admin_Dashboard SHALL display the total number of employees.
2. THE Admin_Dashboard SHALL display the total number of roles.
3. THE Admin_Dashboard SHALL display the total number of documents.
4. THE Admin_Dashboard SHALL display the number of documents whose status is "PROCESSING".
5. THE Admin_Dashboard SHALL display the 10 most recent Audit_Log entries ordered by timestamp descending, where each entry represents a create, update, or delete action performed by an Admin.
6. THE Admin_Dashboard SHALL NOT use any of the following terms in visible labels or descriptions: "vector chunks", "ChromaDB", "embeddings", "distance threshold".

### Requirement 7: Employee Management

**User Story:** As an Admin, I want to manage employees in a professional table view, so that I can create, view, assign roles, and deactivate employees.

#### Acceptance Criteria

1. THE Employees page SHALL display a table with columns: Employee name, Employee ID, Email, Assigned roles, Status, and Actions.
2. WHEN an Admin submits the create-employee form with a valid name and a valid email address, THE System SHALL create the employee record and add the employee to the table with status "Active".
3. WHEN a new employee is created, THE System SHALL NOT assign any role to the employee by default; the Assigned roles column SHALL be empty.
4. WHEN an Admin clicks the view action for an employee row, THE Router SHALL navigate to the Employee Detail page for that employee.
5. WHEN an Admin submits a role assignment on the Employee Detail page, THE System SHALL add the role to the employee's assigned roles and reflect the change in the Assigned roles column of the Employees table.
6. WHEN an Admin removes a role on the Employee Detail page, THE System SHALL remove the role from the employee's assigned roles and reflect the change in the Assigned roles column.
7. WHEN an Admin activates the deactivate action for an employee, THE System SHALL update the employee's status to "Inactive".
8. WHEN an employee is deactivated, THE System SHALL display the employee's status as "Inactive" in the Status column.
9. IF the create-employee form is submitted with an email address that already exists, THEN THE System SHALL display an error message stating that an account with that email already exists.
10. IF no roles exist in the system when an Admin attempts to assign a role, THEN THE System SHALL display a message stating that no roles are available.

### Requirement 8: Employee Detail

**User Story:** As an Admin, I want a detail page for each employee, so that I can see their full profile and manage their role assignments.

#### Acceptance Criteria

1. THE Employee_Detail page SHALL display the employee's name, Employee ID, email address, status, and all currently assigned roles identified by their role names. IF the employee has no assigned roles, THEN THE System SHALL display a message indicating no roles have been assigned.
2. WHEN an Admin selects a role from the "Add Role" control and confirms, THE System SHALL assign that role to the employee and update the displayed assigned roles list without requiring a page reload. The "Add Role" control SHALL only present roles that are not currently assigned to the employee.
3. WHEN an Admin activates the "Remove Role" action for an assigned role, THE System SHALL remove that role from the employee and update the displayed assigned roles list without requiring a page reload.
4. IF an Admin attempts to assign a role that is already assigned to the employee, THEN THE System SHALL display an error message stating "This role is already assigned to the employee."

### Requirement 9: Role Management

**User Story:** As an Admin, I want to view and manage all roles, so that I can control which documents each role can access.

#### Acceptance Criteria

1. THE Roles page SHALL display all existing roles, each identified by its role name.
2. WHEN an Admin submits the create-role form with a role name between 1 and 50 characters, THE System SHALL create the role and add it to the Roles page.
3. IF an Admin submits the create-role form with a name that matches an existing role name (case-insensitive), THEN THE System SHALL display an error message stating that a role with that name already exists.
4. FOR each role displayed, THE System SHALL show the number of employees currently assigned to that role.
5. FOR each role displayed, THE System SHALL show the names of documents that are accessible by that role. IF a role has no accessible documents, THEN THE System SHALL display a message such as "No documents assigned".
6. WHEN an Admin clicks a role, THE Router SHALL navigate to a Role Detail view that shows the role name, the list of assigned employees, and the list of accessible documents.

### Requirement 10: Document Management

**User Story:** As an Admin, I want to upload and manage documents with role-based access control, so that only authorized employees can query them.

#### Acceptance Criteria

1. THE Documents page SHALL display a table showing: document name, upload date, processing status, assigned roles, and available actions.
2. WHEN an Admin uploads a file using the drag-and-drop interface, THE System SHALL accept files of types PDF, TXT, DOCX, DOC, MD, CSV, and JSON up to a maximum size of 50 MB.
3. WHEN an upload is submitted, THE System SHALL immediately display the document's processing status as "Processing".
4. WHEN the document's status changes to "Ready", THE System SHALL display the document's status as "Ready".
5. WHEN the document's status changes to "Failed", THE System SHALL display the document's status as "Failed".
6. WHEN an Admin assigns a role to a document, THE System SHALL add the role to the document's assigned roles display. IF the role does not exist or is invalid, THE System SHALL display an error message.
7. WHEN an Admin removes a role from a document, THE System SHALL remove the role from the document's assigned roles display. IF removing the role would leave the document with zero assigned roles, THE System SHALL display a confirmation message before proceeding.
8. WHEN an Admin confirms deletion of a document, THE System SHALL remove the document from the table. IF the document is not found, THE System SHALL display an error message.
9. IF an Admin attempts to upload a file with an unsupported type or a size exceeding 50 MB, THEN THE System SHALL display an error message identifying the reason (unsupported type or file too large) and SHALL NOT submit the file to the backend.

### Requirement 11: Document Upload UX

**User Story:** As an Admin, I want a polished drag-and-drop upload experience, so that uploading documents feels intuitive and professional.

#### Acceptance Criteria

1. THE Document_Upload component SHALL accept files dropped directly onto the upload area.
2. THE Document_Upload component SHALL allow file selection via a file browser dialog restricted to the accepted extensions: .pdf, .txt, .docx, .doc, .md, .csv, .json.
3. WHEN a file is dragged over the upload area, THE Document_Upload component SHALL apply a distinct visual style (such as a highlighted border) to the drop zone to indicate it is an active drop target. WHEN the file leaves the drop zone without being dropped, THE visual style SHALL revert to its default state.
4. WHILE an upload is in progress, THE Document_Upload component SHALL display a loading or progress indicator and disable further upload actions to prevent concurrent uploads.
5. WHEN an upload completes successfully, THE Document_Upload component SHALL display the document's initial status as "Processing" and poll for status updates at intervals not exceeding 5 seconds until the status transitions to "Ready" or "Failed", or until 10 minutes have elapsed.
6. IF an Admin selects or drops a file with an unsupported extension or a size exceeding 50 MB, THEN THE Document_Upload component SHALL display a user-facing error message identifying the specific reason and SHALL NOT initiate an upload.

### Requirement 12: Audit Logs

**User Story:** As an Admin, I want to view a log of administrative actions, so that I can track changes to employees, roles, and documents.

#### Acceptance Criteria

1. THE Audit_Logs page SHALL display the most recent 500 Audit_Log entries ordered by timestamp descending.
2. FOR each audit log entry displayed, THE System SHALL show: the action type (one of: created, updated, deleted), the name or identifier of the affected resource, the name or email of the Admin who performed the action, and the timestamp in a human-readable format.
3. WHEN an authenticated Admin navigates to "/admin/audit-logs", THE System SHALL display the Audit_Logs page.
4. IF a user who is not authenticated as an Admin attempts to access "/admin/audit-logs", THEN THE Router SHALL redirect them without displaying any audit log data.

### Requirement 13: Admin Settings

**User Story:** As an Admin, I want a settings page, so that I have a dedicated area for platform configuration.

#### Acceptance Criteria

1. WHILE a user is authenticated as an Admin, THE Admin sidebar SHALL display a visible, clickable "Settings" link that navigates to "/admin/settings".
2. THE Settings page SHALL display the organization name in an editable field with a character limit of 1 to 100 characters.
3. IF a user who is not authenticated as an Admin attempts to access "/admin/settings", THEN THE Router SHALL redirect them without displaying any settings data.
4. WHEN an Admin submits the settings form with valid values, THE System SHALL save the changes and display a success confirmation. IF the save request fails, THE System SHALL display an error message and preserve the previously saved values.

### Requirement 14: Employee Navigation

**User Story:** As an Employee, I want a navigation sidebar tailored to my access level, so that I can find my workspace features easily.

#### Acceptance Criteria

1. WHILE a user is authenticated as an Employee, THE System SHALL display a sidebar containing navigation links in this order: Dashboard, Ask AI, My Documents.
2. WHILE a user is authenticated as an Employee, THE Employee sidebar SHALL display the user's full name if available, or their email address as a fallback, together with their assigned role names.
3. WHILE a user is authenticated as an Employee, THE Employee sidebar SHALL include a sign-out action that, when activated, terminates the session, removes the stored token, and navigates to "/login".
4. WHILE a user is authenticated as an Employee, THE Employee sidebar SHALL NOT display navigation items including "Employees", "Roles", "Audit Logs", or "Settings".

### Requirement 15: Employee Dashboard

**User Story:** As an Employee, I want a personalized dashboard showing my profile and accessible content, so that I can quickly understand what I have access to.

#### Acceptance Criteria

1. THE Employee_Dashboard SHALL display the authenticated employee's full name.
2. THE Employee_Dashboard SHALL display the authenticated employee's employee ID.
3. THE Employee_Dashboard SHALL display the employee's assigned roles, each identified by its role name.
4. THE Employee_Dashboard SHALL display the count of documents the employee is authorized to access, where "authorized" means at least one of the employee's assigned roles matches a role assigned to the document.
5. THE Employee_Dashboard SHALL display the 5 most recently uploaded documents the employee is authorized to access, sorted by upload date descending, showing each document's filename and upload date.
6. IF the employee has no accessible documents, THEN THE Employee_Dashboard SHALL display an empty state message in place of the recent documents list.
7. THE Employee_Dashboard SHALL NOT use any of the following terms in visible labels: "vector chunks", "embeddings", "ChromaDB".

### Requirement 16: Ask AI — RAG Chat Interface

**User Story:** As an Employee, I want to ask questions and get AI-powered answers sourced from my authorized documents, so that I can find information quickly without reading every document.

#### Acceptance Criteria

1. THE Ask_AI page SHALL provide a text input that accepts questions up to 2000 characters in length, with a submit action.
2. THE Ask_AI page SHALL display the full conversation history of all question-and-answer pairs submitted during the current browser session in chronological order.
3. WHEN a question is submitted, THE System SHALL display a loading indicator while waiting for the AI response.
4. WHEN the AI response is received, THE System SHALL display the answer text in the conversation history.
5. WHEN the AI response includes source citations, THE System SHALL display the source document names. IF the response includes no source citations, THE System SHALL display a message such as "No sources cited".
6. WHEN page or chunk metadata is available in a citation, THE System SHALL display it alongside the source document name.
7. WHEN no conversation has started, THE Ask_AI page SHALL display an empty state containing a prompt encouraging the user to ask a question.
8. IF the AI request fails, THEN THE System SHALL display a user-friendly error message and provide a retry control that resubmits the same question.
9. IF no AI response is received within 30 seconds, THEN THE System SHALL display a timeout error message and provide a retry control.
10. WHEN the AI response includes an "ungrounded" flag indicating the answer could not be sourced from documents, THE System SHALL display a notice informing the user that the answer may not be based on their authorized documents.
11. THE Ask_AI page SHALL NOT display any of the following in visible UI: "top-k", "distance threshold", "temperature", model names, embedding model names, or vector database names.

### Requirement 17: My Documents

**User Story:** As an Employee, I want to see only the documents I am authorized to access, so that I know what knowledge is available to me.

#### Acceptance Criteria

1. WHEN an authenticated Employee loads the My_Documents page, THE System SHALL display only documents whose status is "READY" and that have at least one role matching a role assigned to the authenticated employee.
2. FOR each document displayed, THE System SHALL show the document's filename and upload date formatted as YYYY-MM-DD.
3. WHEN the employee has no accessible documents, THE System SHALL display an empty state containing a human-readable message explaining that no documents are currently available.
4. FOR each accessible document, THE System SHALL display an "Available" indicator but SHALL NOT display the document's assigned roles list, processing status details, or any other admin-level metadata.
5. IF a user who is not authenticated attempts to access the My_Documents page, THEN THE Router SHALL redirect them to "/login".

### Requirement 18: API Isolation

**User Story:** As a developer, I want all backend API calls isolated in a single module, so that connecting the frontend to the real backend later requires changes in one place only.

#### Acceptance Criteria

1. THE API_Client module SHALL contain all functions that make HTTP requests to the backend.
2. IF any component or hook in the System makes an HTTP request directly (using fetch, axios, XMLHttpRequest, or any equivalent mechanism) outside of the API_Client module, THEN that code SHALL be considered a violation of this requirement.
3. THE Mock_Layer SHALL provide mock implementations that match the API_Client in function names, parameter lists, and return value shapes, so that switching from mock to live data requires only changing the import source.
4. WHEN VITE_API_BASE_URL is set to a non-empty string in the environment, THE API_Client SHALL use that value as the base URL prefix for all requests.
5. IF VITE_API_BASE_URL is not set or is set to an empty string, THEN THE API_Client SHALL use "http://localhost:8000" as the base URL.

### Requirement 19: Design and UX Quality

**User Story:** As a user of any role, I want a professional, readable interface, so that I feel confident using an enterprise platform.

#### Acceptance Criteria

1. THE System SHALL use no more than 2 typefaces, a single accent color, and establish visual hierarchy exclusively through font size and font weight contrast, applied consistently across all pages.
2. THE System SHALL display, for every page that can have no data, an empty state that contains a human-readable explanatory message and a context-appropriate call-to-action (such as a button or link to create the first item or return to a previous page).
3. THE System SHALL display, for every async operation, a visible spinner or skeleton placeholder that is present for the full duration of the operation.
4. THE System SHALL display, for every page where an async operation can fail, an error state that contains a human-readable description of the problem and either a retry control or a navigation path to recover.
5. THE System SHALL be usable on screens from 375px wide (mobile) up to full desktop widths, with no horizontal scrollbar, no clipped content, and all interactive targets at least 44×44px.
6. THE System SHALL NOT use non-user-initiated transitions longer than 400ms, looping background animations, or full-viewport decorative illustrations.
7. THE System SHALL NOT display stack traces, variable names, module paths, raw HTTP error codes, or any other internal implementation details in any visible UI label, placeholder, description, or page title.
