# UPI-Recon Project Documentation

## Project Overview
UPI-Recon is a comprehensive bank reconciliation system designed for matching transactions across CBS (Core Banking System), Switch, and NPCI (National Payments Corporation of India) systems. The system automates the reconciliation process, handles exceptions, provides audit trails, and includes a chatbot for transaction inquiries. It supports GL (General Ledger) proofing, rollback mechanisms, and settlement voucher generation.

The project consists of two main components:
- **Backend**: Python-based API server using FastAPI
- **Frontend**: React/TypeScript web application

## Tech Stack

### Backend
- **Language**: Python 3.x
- **Framework**: FastAPI (REST API)
- **ASGI Server**: Uvicorn
- **Data Processing**: Pandas, Openpyxl (Excel handling)
- **Logging**: Loguru, Python logging
- **Dependencies**: See `backend/requirements.txt`
  - fastapi==0.104.1
  - uvicorn[standard]==0.24.0
  - pandas==2.1.3
  - python-multipart==0.0.6
  - openpyxl==3.1.2
  - xlrd==2.0.1
  - python-dotenv
  - requests
  - loguru==0.7.2

### Frontend
- **Language**: TypeScript
- **Framework**: React 19.2.0
- **Build Tool**: Vite
- **Styling**: Tailwind CSS, PostCSS
- **UI Components**: Shadcn/ui (Radix UI primitives)
- **State Management**: TanStack Query (React Query)
- **HTTP Client**: Axios
- **Routing**: React Router DOM
- **Icons**: Lucide React
- **Dependencies**: See `frontend/package.json`
  - React ecosystem with hooks, forms, charts, etc.

## Project Structure and File Descriptions

### Root Level Files
- `README.md`: Project overview (currently contains placeholder text "Tera Bhai Seedhe Maut")
- `Actual_changes_needed.md`: Documentation of required changes
- `API_INTEGRATION_TEST.md`: API testing documentation
- `Change_needed_by_them.md`: Change requests from stakeholders

### Backend Directory (`backend/`)

#### Core Application Files
- `app.py`: Main FastAPI application file
  - Defines all API endpoints
  - Handles file uploads, reconciliation runs, chatbot queries
  - Integrates all modules (recon engine, audit trail, exception handling, etc.)
  - CORS configuration for frontend integration
  - Health check endpoints

- `recon_engine.py`: Core reconciliation logic
  - Processes transaction dataframes
  - Performs RRN + Amount + Date matching
  - Generates reports and adjustment CSVs
  - Handles force matching functionality
  - Categorizes transactions as MATCHED, PARTIAL_MATCH, ORPHAN, MISMATCH

- `file_handler.py`: File processing utilities
  - Loads and validates uploaded files
  - Handles different file formats (Excel, CSV)
  - Preprocesses data (missing values, data types)

- `config.py`: Configuration constants
  - Run ID format, directory paths
  - System-wide settings

- `logging_config.py`: Logging setup
  - Configures structured logging with JSON output
  - Logger initialization

#### Advanced Features
- `audit_trail.py`: Comprehensive audit logging system
  - Tracks all user actions and system events
  - Compliance reporting
  - Audit trail management with rotation
  - User activity monitoring

- `exception_handler.py`: Exception management
  - Handles various error scenarios (SFTP failures, timeouts, validation errors)
  - Recovery strategies
  - Exception logging and resolution

- `rollback_manager.py`: Rollback functionality
  - Supports different rollback levels (ingestion, mid-recon, cycle-wise, accounting)
  - Safe rollback operations with validation

- `gl_proofing_engine.py`: General Ledger proofing
  - Creates GL proofing reports
  - Variance bridge management
  - Aging analysis for variances

- `settlement_engine.py`: Settlement and voucher generation
  - Generates accounting vouchers from reconciled data
  - Settlement amount calculations

#### Chatbot Services (`chatbot_services/`)
- `app.py`: Chatbot API endpoints
- `lookup.py`: Transaction lookup functionality
- `nlp.py`: Natural language processing utilities
- `response_formatter.py`: Response formatting for chatbot
- `chat_cli.py`: Command-line interface for chatbot
- `test.py`: Testing utilities
- `API_Documentation.md`: Chatbot API docs

#### Data and Scripts
- `data/uploads/`: Directory for uploaded files
- `data/output/`: Directory for generated reports and outputs
- `scripts/fix_output_and_keys.py`: Utility script for data fixes

#### Documentation and Config
- `README.me`: Backend setup instructions
- `API_DOC.md`: API documentation
- `.gitignore`: Git ignore rules

### Frontend Directory (`frontend/`)

#### Build and Config Files
- `package.json`: Node.js dependencies and scripts
- `vite.config.ts`: Vite build configuration
- `tsconfig.json/tsconfig.app.json/tsconfig.node.json`: TypeScript configs
- `tailwind.config.ts`: Tailwind CSS configuration
- `postcss.config.js`: PostCSS setup
- `eslint.config.js`: ESLint configuration
- `components.json`: Shadcn/ui component config

#### Public Assets (`public/`)
- Favicon files, manifest files, icons

#### Source Code (`src/`)
- `App.tsx`: Main React application component
- `main.tsx`: Application entry point
- `index.css/App.css`: Global styles

#### Components (`components/`)
- `Layout.tsx`: Main layout component
- `LoadingScreen.tsx`: Loading UI
- `NavLink.tsx`: Navigation link component
- `TypingIndicator.tsx`: Chatbot typing indicator

##### UI Components (`ui/`)
- Extensive Shadcn/ui component library:
  - Form components (button, input, select, etc.)
  - Layout components (card, dialog, sheet, etc.)
  - Data display (table, chart, etc.)
  - Navigation (tabs, sidebar, etc.)

#### Pages (`pages/`)
- `Dashboard.tsx`: Main dashboard
- `FileUpload.tsx`: File upload interface
- `Recon.tsx`: Reconciliation interface
- `Audit.tsx`: Audit trail viewer
- `Reports.tsx`: Report generation
- `GLProofing.tsx`: GL proofing interface
- `ForceMatch.tsx`: Force matching UI
- `AutoMatch.tsx`: Auto-matching configuration
- `Unmatched.tsx`: Unmatched transactions view
- `Rollback.tsx`: Rollback operations
- `Enquiry.tsx`: Transaction enquiry
- `ViewStatus.tsx`: Status viewing
- `NotFound.tsx`: 404 page
- `PlaceholderPage.tsx`: Placeholder component

#### Hooks and Utils (`hooks/`, `lib/`)
- `use-mobile.tsx`: Mobile detection hook
- `use-toast.ts`: Toast notification hook
- `api.ts`: API client utilities
- `utils.ts`: General utilities

## How Files Connect and Project Workflow

### Data Flow
1. **File Upload** (`FileUpload.tsx` → `app.py` `/api/v1/upload`)
   - Frontend uploads files to backend
   - `file_handler.py` processes and validates files
   - Files stored in `data/uploads/`

2. **Reconciliation Process** (`Recon.tsx` → `app.py` `/api/v1/recon/run`)
   - `recon_engine.py` performs matching logic
   - Uses `audit_trail.py` for logging
   - `exception_handler.py` manages errors
   - Outputs saved to `data/output/`

3. **Chatbot Integration**
   - `lookup.py` searches reconciled data
   - `nlp.py` processes queries
   - `response_formatter.py` formats responses
   - Integrated into main `app.py`

4. **Advanced Features**
   - GL Proofing: `gl_proofing_engine.py` creates reports
   - Rollback: `rollback_manager.py` handles reversals
   - Settlement: `settlement_engine.py` generates vouchers

### Frontend-Backend Integration
- Frontend uses `api.ts` to call backend endpoints
- CORS configured in `app.py` for localhost:5173 (Vite dev server)
- Real-time updates via polling or websockets (not implemented yet)

### Key Dependencies
- Backend modules imported in `app.py`
- Frontend components use shared UI library
- Data flows from uploads → processing → outputs → frontend display

## Project Purpose and Functionality

UPI-Recon automates bank reconciliation for UPI transactions by:
- Matching transactions across multiple systems (CBS, Switch, NPCI)
- Identifying discrepancies and exceptions
- Providing audit trails for compliance
- Offering chatbot for quick transaction lookups
- Supporting GL proofing and settlement processes
- Enabling manual interventions (force match, rollback)

The system reduces manual effort in reconciliation, improves accuracy, and provides comprehensive reporting for financial operations.

## Setup and Running

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Future Enhancements
- Real-time reconciliation
- Advanced ML-based matching
- Multi-bank support
- Enhanced reporting dashboards
