# Project Overview: Visual POS Automation for FulôFiló  
## 1. What We Are Doing  
We are developing a custom ****Visual Point of Sale (POS) System**** for FulôFiló.  
Unlike a traditional retail checkout that relies on cashiers manually typing in items or scanning printed barcodes, this system uses an overhead High-Definition camera and Artificial Intelligence (Computer Vision) to "look" at the items placed on the counter. The AI instantly identifies the products (e.g., "necessaire_stylo", "carteira_alca", "chaveiro_metal_redondo"), counts them, and automatically logs the transaction into a digital database.  
The system is decoupled:  
* ****Capture (The Store):**** A simple camera setup over the checkout mat.  
* ****Processing (The Home Office):**** An iMac M3 running a locally trained YOLO (You Only Look Once) object detection model.  
* ****Automation:**** N8N software bridging the camera images to the AI and logging the output.  
## 2. Why We Are Doing It (The Goal)  
The primary goal of this project is to ****improve visibility, organization, and operational speed**** during checkout, addressing the specific constraints and advantages of FulôFiló.  
## Key Drivers:  
* ****Speed During Peak Hours:**** FulôFiló experiences intense, concentrated bursts of tourists, particularly around sunset (15h-16h and 17h20-18h20). Manually counting high-volume, low-cost items (like the 4,341 **chaveiros 10** or 6,901 **nécessaires** sold annually) causes bottlenecks. Computer Vision can process a tray of mixed items in under 2 seconds.  
* ****The "No Barcode" Constraint:**** The store's products are highly visual, culturally themed (FARM aesthetic), and supplied without barcodes. Implementing a traditional barcode system would require massive operational overhead (printing, tagging, updating). A visual system completely bypasses this need.  
* ****Data Integrity & Auditability:**** By replacing manual entry with AI detection, we drastically reduce human error (e.g., miscounting keychains or mistyping a product name). Furthermore, because every transaction generates an image, there is a perfect visual audit trail for every sale, which is highly advantageous for accurate tax and revenue tracking.  
* ****Future-Proofing Inventory Intelligence:**** While the initial phase focuses on counting product categories (e.g., "wallet"), the visual data collected lays the groundwork for phase two: tracking exact prints (e.g., "wallet_cactus_print" vs. "wallet_leopard_print") to optimize purchasing based on localized trends.  
## 3. How We Are Doing It (The Methodology)  
We are executing this through a phased, iterative approach leveraging local, high-performance computing.  
## Phase 1: Standardization & Data Preparation (Current Phase)  
* ****Action:**** Establishing a strict, machine-readable naming convention (categoria_tipo_detalhe) for the top-selling items to ensure data cleanly maps to databases (e.g., converting "Canga areia" to canga_areia).  
* ****Action:**** Taking sample photos of products, cropping them natively on macOS using Swift, and sorting them into an AI-ready folder structure to create the initial dataset.  
## Phase 2: AI Model Training (Local Apple Silicon)  
* ****Action:**** Gathering 50-100 realistic photos of the checkout counter with various combinations of the top three items (**carteiras, nécessaires, chaveiros**).  
* ****Action:**** Using a labeling tool to draw bounding boxes around the items and generating the data.yaml manifest.  
* ****Action:**** Training a YOLO object detection model natively on the iMac M3. The M3 chip provides significant processing power, keeping the training fast and the data 100% private and local.  
## Phase 3: Hardware & Automation Deployment  
* ****Action:**** Installing a top-down camera (e.g., a PoE IP Camera) at the store checkout counter.  
* ****Action:**** Configuring N8N to act as the bridge: detecting when a new checkout photo is snapped, sending it to the locally hosted YOLO model on the M3, receiving the JSON output (the count and type of items), and logging that data into a spreadsheet or database mimicking the current PDF reports.  
