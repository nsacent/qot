"""Canonical advert specifications shared by every QOT environment.

Keep each category focused: three to six useful buyer-facing fields, all optional.
The catalog is keyed by the stable category slug seeded by QOT.
"""


def field(key, name, filter_type="text", options=()):
    return {
        "key": key,
        "name": name,
        "filter_type": filter_type,
        "options": tuple(options),
    }


YES_NO = ("Yes", "No")
CONDITION = ("Brand New", "Used", "Refurbished")
GENDER = ("Men", "Women", "Unisex", "Children")
COLORS = ("Black", "White", "Blue", "Red", "Green", "Brown", "Grey", "Other")
PHONE_BRANDS = (
    "Apple", "Samsung", "Tecno", "Infinix", "Itel", "Huawei", "Xiaomi",
    "Oppo", "Vivo", "Nokia", "Google", "Other",
)
COMPUTER_BRANDS = (
    "Apple", "Dell", "HP", "Lenovo", "Asus", "Acer", "Microsoft",
    "Samsung", "Toshiba", "MSI", "Other",
)
VEHICLE_MAKES = (
    "Toyota", "Nissan", "Subaru", "Mercedes-Benz", "BMW", "Honda", "Mazda",
    "Mitsubishi", "Isuzu", "Suzuki", "Ford", "Kia", "Hyundai", "Other",
)
MOTORCYCLE_MAKES = (
    "Bajaj", "TVS", "Honda", "Yamaha", "Suzuki", "Kawasaki", "Hero", "Other",
)
SIZES = ("XS", "S", "M", "L", "XL", "XXL", "Other")


FILTER_SPECS_BY_SLUG = {
    # Vehicles
    "cars": (
        field("make", "Make", "select", VEHICLE_MAKES),
        field("model", "Model"),
        field("year", "Year", "number"),
        field("mileage", "Mileage (km)", "number"),
        field("transmission", "Transmission", "select", ("Automatic", "Manual")),
        field("fuel", "Fuel Type", "select", ("Petrol", "Diesel", "Hybrid", "Electric")),
    ),
    "motorcycles": (
        field("make", "Make", "select", MOTORCYCLE_MAKES),
        field("model", "Model"), field("year", "Year", "number"),
        field("engine_size", "Engine Size (cc)", "number"),
        field("mileage", "Mileage (km)", "number"),
    ),
    "trucks": (
        field("make", "Make", "select", VEHICLE_MAKES), field("model", "Model"),
        field("year", "Year", "number"), field("mileage", "Mileage (km)", "number"),
        field("capacity", "Load Capacity"),
    ),
    "buses": (
        field("make", "Make", "select", VEHICLE_MAKES), field("model", "Model"),
        field("year", "Year", "number"), field("seating_capacity", "Seating Capacity", "number"),
        field("mileage", "Mileage (km)", "number"),
    ),
    "car-parts": (
        field("part_type", "Part Type"), field("make_compatibility", "Compatible Make"),
        field("model_compatibility", "Compatible Model"),
        field("part_condition", "Part Condition", "select", CONDITION),
    ),
    "motorcycle-parts": (
        field("part_type", "Part Type"), field("make_compatibility", "Compatible Make"),
        field("model_compatibility", "Compatible Model"),
        field("part_condition", "Part Condition", "select", CONDITION),
    ),
    "tyres-wheels": (
        field("item_type", "Item Type", "select", ("Tyre", "Rim", "Complete Wheel")),
        field("tyre_size", "Tyre Size"), field("wheel_size", "Wheel Size"),
        field("vehicle_type", "Vehicle Type", "select", ("Car", "Motorcycle", "Truck", "Bus")),
    ),
    "vehicle-services": (
        field("service_type", "Service Type", "select", ("Repair", "Diagnostics", "Servicing", "Body Work", "Towing", "Car Wash", "Other")),
        field("vehicle_type", "Vehicle Type", "select", ("Car", "Motorcycle", "Truck", "Bus", "Heavy Equipment")),
        field("service_location", "Service Location", "select", ("Workshop", "Mobile Service", "Both")),
    ),
    "boats": (
        field("boat_type", "Boat Type", "select", ("Fishing", "Passenger", "Speed Boat", "Canoe", "Other")),
        field("make", "Make"), field("year", "Year", "number"),
        field("engine_type", "Engine Type", "select", ("Outboard", "Inboard", "No Engine")),
    ),
    "heavy-equipment": (
        field("equipment_type", "Equipment Type"), field("make", "Make"),
        field("model", "Model"), field("year", "Year", "number"),
        field("operating_hours", "Operating Hours", "number"),
    ),

    # Electronics
    "mobile-phones": (
        field("brand", "Brand", "select", PHONE_BRANDS), field("model", "Model"),
        field("storage", "Storage", "select", ("16GB", "32GB", "64GB", "128GB", "256GB", "512GB", "1TB")),
        field("ram", "RAM", "select", ("2GB", "3GB", "4GB", "6GB", "8GB", "12GB", "16GB")),
        field("network", "Network", "select", ("3G", "4G LTE", "5G")),
    ),
    "laptops-computers": (
        field("brand", "Brand", "select", COMPUTER_BRANDS), field("model", "Model"),
        field("processor", "Processor"),
        field("ram", "RAM", "select", ("4GB", "8GB", "16GB", "32GB", "64GB+")),
        field("storage", "Storage", "select", ("128GB", "256GB", "512GB", "1TB", "2TB+")),
        field("storage_type", "Storage Type", "select", ("SSD", "HDD", "SSD + HDD", "eMMC")),
    ),
    "tablets": (
        field("brand", "Brand", "select", PHONE_BRANDS), field("model", "Model"),
        field("storage", "Storage", "select", ("32GB", "64GB", "128GB", "256GB", "512GB", "1TB")),
        field("ram", "RAM", "select", ("2GB", "3GB", "4GB", "6GB", "8GB", "12GB+")),
        field("connectivity", "Connectivity", "select", ("Wi-Fi", "Wi-Fi + Cellular")),
    ),
    "tvs": (
        field("brand", "Brand"), field("screen_size", "Screen Size (inches)", "number"),
        field("display_type", "Display Type", "select", ("LED", "OLED", "QLED", "LCD")),
        field("resolution", "Resolution", "select", ("HD", "Full HD", "4K", "8K")),
        field("smart_tv", "Smart TV", "boolean"),
    ),
    "cameras": (
        field("brand", "Brand"),
        field("camera_type", "Camera Type", "select", ("DSLR", "Mirrorless", "Compact", "Action", "CCTV", "Other")),
        field("megapixels", "Megapixels", "number"), field("lens_mount", "Lens / Mount"),
    ),
    "audio-speakers": (
        field("brand", "Brand"),
        field("audio_type", "Audio Type", "select", ("Speaker", "Soundbar", "Home Theatre", "Headphones", "Amplifier", "Other")),
        field("connectivity", "Connectivity", "select", ("Bluetooth", "Wired", "Wi-Fi", "Multiple")),
        field("power_source", "Power Source", "select", ("Mains", "Battery", "Rechargeable")),
    ),
    "computer-accessories": (
        field("accessory_type", "Accessory Type"), field("brand", "Brand"),
        field("compatibility", "Compatibility"),
        field("connectivity", "Connectivity", "select", ("Wired", "Wireless", "Not Applicable")),
    ),
    "gaming-consoles": (
        field("brand", "Brand", "select", ("PlayStation", "Xbox", "Nintendo", "Other")),
        field("console_model", "Console Model"), field("storage", "Storage"),
        field("includes_games", "Includes Games", "boolean"),
    ),
    "smart-watches": (
        field("brand", "Brand"), field("model", "Model"),
        field("compatibility", "Phone Compatibility", "select", ("Android", "iPhone", "Android & iPhone")),
        field("connectivity", "Connectivity", "select", ("Bluetooth", "Wi-Fi", "Cellular")),
    ),
    "printers-scanners": (
        field("brand", "Brand"),
        field("device_type", "Device Type", "select", ("Printer", "Scanner", "All-in-One")),
        field("color_printing", "Colour Printing", "boolean"),
        field("connectivity", "Connectivity", "select", ("USB", "Wi-Fi", "Ethernet", "Multiple")),
    ),

    # Property
    "houses-for-sale": (
        field("bedrooms", "Bedrooms", "number"), field("bathrooms", "Bathrooms", "number"),
        field("property_size", "Property Size"),
        field("title_status", "Title Status", "select", ("Private Mailo", "Freehold", "Leasehold", "Customary", "Agreement")),
        field("parking", "Parking", "boolean"),
    ),
    "houses-for-rent": (
        field("bedrooms", "Bedrooms", "number"), field("bathrooms", "Bathrooms", "number"),
        field("furnished", "Furnishing", "select", ("Furnished", "Semi-furnished", "Unfurnished")),
        field("parking", "Parking", "boolean"),
        field("rent_period", "Rent Period", "select", ("Daily", "Monthly", "Yearly")),
    ),
    "apartments-for-rent": (
        field("bedrooms", "Bedrooms", "number"), field("bathrooms", "Bathrooms", "number"),
        field("furnished", "Furnishing", "select", ("Furnished", "Semi-furnished", "Unfurnished")),
        field("parking", "Parking", "boolean"), field("floor", "Floor"),
    ),
    "land-for-sale": (
        field("land_size", "Land Size", "number"),
        field("land_unit", "Land Unit", "select", ("Decimals", "Acres", "Hectares", "Square Metres")),
        field("title_status", "Title Status", "select", ("Private Mailo", "Freehold", "Leasehold", "Customary", "Agreement")),
        field("land_use", "Land Use", "select", ("Residential", "Commercial", "Agricultural", "Industrial", "Mixed Use")),
        field("road_access", "Road Access", "boolean"),
    ),
    "commercial-property": (
        field("property_type", "Property Type", "select", ("Shop", "Office", "Warehouse", "Building", "Other")),
        field("purpose", "Purpose", "select", ("For Sale", "For Rent")),
        field("floor_area", "Floor Area"), field("parking", "Parking", "boolean"),
    ),
    "shops-offices": (
        field("property_type", "Property Type", "select", ("Shop", "Office", "Stall", "Salon Space", "Other")),
        field("purpose", "Purpose", "select", ("For Sale", "For Rent")),
        field("floor_area", "Floor Area"),
        field("furnished", "Furnished", "boolean"),
    ),
    "short-stay-rentals": (
        field("property_type", "Property Type", "select", ("Apartment", "House", "Room", "Cottage")),
        field("bedrooms", "Bedrooms", "number"), field("furnished", "Furnished", "boolean"),
        field("guests", "Maximum Guests", "number"),
    ),
    "hostels-rentals": (
        field("room_type", "Room Type", "select", ("Single", "Double", "Shared", "Bedsitter")),
        field("self_contained", "Self-contained", "boolean"), field("furnished", "Furnished", "boolean"),
        field("bathroom_type", "Bathroom Type", "select", ("Private", "Shared", "Outside")),
    ),

    # Fashion
    "mens-clothing": (field("item_type", "Item Type"), field("size", "Size", "select", SIZES), field("brand", "Brand"), field("material", "Material"), field("color", "Colour", "select", COLORS)),
    "womens-clothing": (field("item_type", "Item Type"), field("size", "Size", "select", SIZES), field("brand", "Brand"), field("material", "Material"), field("color", "Colour", "select", COLORS)),
    "shoes": (field("shoe_type", "Shoe Type"), field("size", "Size"), field("brand", "Brand"), field("material", "Material")),
    "bags": (field("bag_type", "Bag Type"), field("brand", "Brand"), field("material", "Material"), field("color", "Colour", "select", COLORS)),
    "watches": (field("watch_type", "Watch Type", "select", ("Analogue", "Digital", "Smart", "Hybrid")), field("brand", "Brand"), field("movement", "Movement", "select", ("Quartz", "Automatic", "Mechanical", "Digital")), field("material", "Material")),
    "jewellery": (field("jewellery_type", "Jewellery Type"), field("material", "Material"), field("gender", "For", "select", GENDER)),
    "childrens-clothing": (field("item_type", "Item Type"), field("age_group", "Age Group"), field("size", "Size"), field("gender", "For", "select", ("Boys", "Girls", "Unisex"))),
    "wedding-wear": (field("item_type", "Item Type"), field("gender", "For", "select", GENDER), field("size", "Size"), field("rental_available", "Available for Rent", "boolean")),
    "uniforms": (field("uniform_type", "Uniform Type"), field("size", "Size"), field("gender", "For", "select", GENDER), field("custom_made", "Custom Made", "boolean")),

    # Home and furniture
    "sofas": (field("sofa_type", "Sofa Type"), field("seats", "Number of Seats", "number"), field("material", "Material"), field("color", "Colour", "select", COLORS)),
    "beds-mattresses": (field("item_type", "Item Type", "select", ("Bed", "Mattress", "Bed + Mattress")), field("size", "Size"), field("material", "Material"), field("with_mattress", "Includes Mattress", "boolean")),
    "tables-chairs": (field("item_type", "Item Type", "select", ("Table", "Chair", "Table Set", "Desk", "Stool")), field("material", "Material"), field("seats", "Seating Capacity", "number"), field("color", "Colour", "select", COLORS)),
    "wardrobes": (field("material", "Material"), field("doors", "Number of Doors", "number"), field("size", "Size"), field("color", "Colour", "select", COLORS)),
    "kitchen-items": (field("item_type", "Item Type"), field("brand", "Brand"), field("material", "Material"), field("capacity", "Capacity")),
    "home-decor": (field("decor_type", "Decor Type"), field("material", "Material"), field("color", "Colour", "select", COLORS)),
    "lighting": (field("light_type", "Light Type"), field("power_source", "Power Source", "select", ("Mains", "Solar", "Battery", "Rechargeable")), field("color", "Colour", "select", COLORS)),
    "curtains-carpets": (field("item_type", "Item Type", "select", ("Curtain", "Carpet", "Rug", "Blind")), field("size", "Size"), field("material", "Material"), field("color", "Colour", "select", COLORS)),
    "appliances": (field("appliance_type", "Appliance Type"), field("brand", "Brand"), field("capacity", "Capacity"), field("power_source", "Power Source", "select", ("Electric", "Gas", "Solar", "Battery"))),

    # Jobs
    "accounting-finance-jobs": (field("job_type", "Job Type", "select", ("Full-time", "Part-time", "Contract", "Internship")), field("experience_level", "Experience Level", "select", ("Entry", "Mid-level", "Senior")), field("qualification", "Minimum Qualification"), field("salary_period", "Salary Period", "select", ("Monthly", "Weekly", "Daily"))),
    "sales-marketing-jobs": (field("job_type", "Job Type", "select", ("Full-time", "Part-time", "Contract", "Commission")), field("experience_level", "Experience Level", "select", ("Entry", "Mid-level", "Senior")), field("industry", "Industry"), field("remote", "Remote Work", "boolean")),
    "teaching-jobs": (field("job_type", "Job Type", "select", ("Full-time", "Part-time", "Contract")), field("education_level", "Education Level Taught"), field("subject", "Subject"), field("qualification", "Minimum Qualification")),
    "driver-jobs": (field("job_type", "Job Type", "select", ("Full-time", "Part-time", "Contract")), field("licence_class", "Driving Licence Class"), field("vehicle_type", "Vehicle Type"), field("experience_years", "Years of Experience", "number")),
    "hotel-restaurant-jobs": (field("job_type", "Job Type", "select", ("Full-time", "Part-time", "Contract", "Casual")), field("role_type", "Role"), field("experience_level", "Experience Level", "select", ("Entry", "Mid-level", "Senior")), field("live_in", "Accommodation Provided", "boolean")),
    "office-jobs": (field("job_type", "Job Type", "select", ("Full-time", "Part-time", "Contract", "Internship")), field("role_type", "Role"), field("experience_level", "Experience Level", "select", ("Entry", "Mid-level", "Senior")), field("qualification", "Minimum Qualification")),
    "it-jobs": (field("job_type", "Job Type", "select", ("Full-time", "Part-time", "Contract", "Freelance", "Internship")), field("specialisation", "Specialisation"), field("experience_level", "Experience Level", "select", ("Entry", "Mid-level", "Senior")), field("remote", "Remote Work", "boolean")),
    "security-jobs": (field("job_type", "Job Type", "select", ("Full-time", "Part-time", "Contract")), field("role_type", "Role"), field("experience_years", "Years of Experience", "number"), field("training_required", "Security Training Required", "boolean")),
    "part-time-jobs": (field("role_type", "Role"), field("work_schedule", "Work Schedule"), field("experience_level", "Experience Level", "select", ("No Experience", "Entry", "Experienced")), field("remote", "Remote Work", "boolean")),

    # Services
    "computer-repair": (field("service_type", "Service Type", "select", ("Hardware Repair", "Software Repair", "Data Recovery", "Networking", "Other")), field("device_type", "Device Type", "select", ("Laptop", "Desktop", "Printer", "Network Equipment")), field("service_location", "Service Location", "select", ("Workshop", "On-site", "Both")), field("warranty", "Service Warranty", "boolean")),
    "phone-repair": (field("service_type", "Service Type", "select", ("Screen Repair", "Battery", "Charging", "Software", "Water Damage", "Other")), field("supported_brands", "Supported Brands"), field("service_location", "Service Location", "select", ("Workshop", "Pickup", "Both")), field("warranty", "Service Warranty", "boolean")),
    "graphic-design": (field("service_type", "Service Type", "select", ("Logo", "Branding", "Social Media", "Packaging", "UI/UX", "Other")), field("delivery_format", "Delivery Format"), field("revisions", "Revisions Included", "number"), field("remote_service", "Available Remotely", "boolean")),
    "printing-services": (field("print_type", "Print Type", "select", ("Documents", "Business Cards", "Banners", "T-shirts", "Large Format", "Other")), field("colour", "Colour Printing", "boolean"), field("minimum_quantity", "Minimum Quantity", "number"), field("delivery_available", "Delivery Available", "boolean")),
    "cleaning-services": (field("service_type", "Service Type", "select", ("Home", "Office", "Move-in/Out", "Carpet", "Industrial")), field("billing_unit", "Billing Unit", "select", ("Per Visit", "Per Hour", "Per Day", "Contract")), field("supplies_included", "Supplies Included", "boolean"), field("service_location", "Areas Served")),
    "construction-services": (field("service_type", "Service Type", "select", ("Building", "Renovation", "Plumbing", "Electrical", "Roofing", "Other")), field("project_type", "Project Type", "select", ("Residential", "Commercial", "Industrial")), field("materials_included", "Materials Included", "boolean"), field("service_location", "Areas Served")),
    "transport-services": (field("service_type", "Service Type", "select", ("Goods", "Passenger", "Moving", "Courier", "Towing")), field("vehicle_type", "Vehicle Type"), field("service_area", "Service Area", "select", ("Local", "Nationwide", "Cross-border")), field("capacity", "Capacity")),
    "event-services": (field("service_type", "Service Type", "select", ("Planning", "Decoration", "Catering", "Sound", "Tents & Chairs", "Other")), field("event_type", "Event Type"), field("maximum_guests", "Maximum Guests", "number"), field("equipment_included", "Equipment Included", "boolean")),
    "photography-video": (field("service_type", "Service Type", "select", ("Photography", "Videography", "Drone", "Editing", "Full Package")), field("event_type", "Event Type"), field("delivery_format", "Delivery Format"), field("travel_available", "Travel Available", "boolean")),
    "legal-services": (field("service_type", "Service Type", "select", ("Consultation", "Documents", "Land", "Business", "Family", "Court Representation")), field("delivery_mode", "Delivery Mode", "select", ("In Person", "Online", "Both")), field("licensed_provider", "Licensed Provider", "boolean")),
    "business-services": (field("service_type", "Service Type", "select", ("Registration", "Accounting", "Tax", "Consulting", "Secretarial", "Other")), field("business_size", "Business Size", "select", ("Individual", "Small Business", "Company", "Organisation")), field("remote_service", "Available Remotely", "boolean")),
    "beauty-services": (field("service_type", "Service Type", "select", ("Hair", "Makeup", "Nails", "Massage", "Spa", "Other")), field("client_type", "Client Type", "select", GENDER), field("service_location", "Service Location", "select", ("Salon", "Mobile", "Both")), field("appointment_required", "Appointment Required", "boolean")),

    # Agriculture
    "farm-animals": (field("animal_type", "Animal Type"), field("breed", "Breed"), field("age", "Age"), field("sex", "Sex", "select", ("Male", "Female", "Mixed")), field("quantity", "Quantity", "number")),
    "poultry": (field("bird_type", "Bird Type", "select", ("Chicken", "Turkey", "Duck", "Guinea Fowl", "Other")), field("breed", "Breed"), field("age", "Age"), field("purpose", "Purpose", "select", ("Layers", "Broilers", "Breeding", "Mixed")), field("quantity", "Quantity", "number")),
    "seeds": (field("crop_type", "Crop Type"), field("variety", "Variety"), field("package_size", "Package Size"), field("certified", "Certified Seed", "boolean")),
    "fertilizers": (field("fertilizer_type", "Fertilizer Type", "select", ("Organic", "Inorganic", "Foliar", "Soil Conditioner")), field("brand", "Brand"), field("package_size", "Package Size"), field("crop_use", "Recommended Crop")),
    "farm-tools": (field("tool_type", "Tool Type"), field("brand", "Brand"), field("power_source", "Power Source", "select", ("Manual", "Petrol", "Diesel", "Electric", "Solar")), field("capacity", "Capacity")),
    "animal-feeds": (field("animal_type", "For Animal"), field("feed_type", "Feed Type"), field("brand", "Brand"), field("package_size", "Package Size")),
    "fresh-produce": (field("produce_type", "Produce Type"), field("variety", "Variety"), field("quantity", "Quantity", "number"), field("unit", "Unit", "select", ("Kilogram", "Sack", "Crate", "Bunch", "Piece"))),
    "agricultural-land": (field("land_size", "Land Size", "number"), field("land_unit", "Land Unit", "select", ("Decimals", "Acres", "Hectares")), field("tenure", "Tenure", "select", ("For Sale", "For Rent", "Lease")), field("water_source", "Water Source"), field("suitable_for", "Suitable For")),

    # Health and beauty
    "skin-care": (field("product_type", "Product Type"), field("brand", "Brand"), field("skin_type", "Skin Type", "select", ("Normal", "Dry", "Oily", "Combination", "Sensitive", "All")), field("size", "Size / Volume")),
    "hair-products": (field("product_type", "Product Type"), field("brand", "Brand"), field("hair_type", "Hair Type"), field("size", "Size / Volume")),
    "makeup": (field("product_type", "Product Type"), field("brand", "Brand"), field("shade", "Shade"), field("size", "Size / Volume")),
    "perfumes": (field("brand", "Brand"), field("fragrance_name", "Fragrance Name"), field("gender", "For", "select", GENDER), field("volume", "Volume (ml)", "number")),
    "salon-equipment": (field("equipment_type", "Equipment Type"), field("brand", "Brand"), field("power_source", "Power Source", "select", ("Electric", "Manual", "Rechargeable")), field("professional_grade", "Professional Grade", "boolean")),
    "fitness-equipment": (field("equipment_type", "Equipment Type"), field("brand", "Brand"), field("maximum_weight", "Maximum User Weight"), field("foldable", "Foldable", "boolean")),
    "personal-care": (field("product_type", "Product Type"), field("brand", "Brand"), field("target_user", "For", "select", GENDER), field("size", "Size / Volume")),

    # Baby and kids
    "baby-clothes": (field("item_type", "Item Type"), field("age_group", "Age Group"), field("size", "Size"), field("gender", "For", "select", ("Boys", "Girls", "Unisex"))),
    "baby-shoes": (field("shoe_type", "Shoe Type"), field("age_group", "Age Group"), field("size", "Size"), field("gender", "For", "select", ("Boys", "Girls", "Unisex"))),
    "toys": (field("toy_type", "Toy Type"), field("age_group", "Age Group"), field("material", "Material"), field("battery_required", "Battery Required", "boolean")),
    "baby-furniture": (field("item_type", "Item Type"), field("age_group", "Age Group"), field("material", "Material"), field("foldable", "Foldable", "boolean")),
    "school-items": (field("item_type", "Item Type"), field("school_level", "School Level", "select", ("Nursery", "Primary", "Secondary", "University")), field("brand", "Brand"), field("quantity", "Quantity", "number")),
    "kids-accessories": (field("accessory_type", "Accessory Type"), field("age_group", "Age Group"), field("gender", "For", "select", ("Boys", "Girls", "Unisex")), field("color", "Colour", "select", COLORS)),

    # Sports and hobbies
    "gym-equipment": (field("equipment_type", "Equipment Type"), field("brand", "Brand"), field("weight", "Weight"), field("commercial_grade", "Commercial Grade", "boolean")),
    "bicycles": (field("bicycle_type", "Bicycle Type", "select", ("Mountain", "Road", "BMX", "Kids", "Electric", "Other")), field("brand", "Brand"), field("frame_size", "Frame Size"), field("wheel_size", "Wheel Size")),
    "sports-wear": (field("sport", "Sport"), field("item_type", "Item Type"), field("size", "Size", "select", SIZES), field("gender", "For", "select", GENDER)),
    "musical-instruments": (field("instrument_type", "Instrument Type"), field("brand", "Brand"), field("skill_level", "Skill Level", "select", ("Beginner", "Intermediate", "Professional")), field("electric", "Electric / Amplified", "boolean")),
    "books": (field("book_type", "Book Type", "select", ("Textbook", "Novel", "Children's", "Religious", "Professional", "Other")), field("title", "Book Title"), field("author", "Author"), field("language", "Language")),
    "art-crafts": (field("item_type", "Item Type"), field("art_style", "Style"), field("material", "Material"), field("dimensions", "Dimensions")),

    # Pets
    "dogs": (field("breed", "Breed"), field("age", "Age"), field("sex", "Sex", "select", ("Male", "Female")), field("vaccinated", "Vaccinated", "boolean"), field("pedigree", "Pedigree", "boolean")),
    "cats": (field("breed", "Breed"), field("age", "Age"), field("sex", "Sex", "select", ("Male", "Female")), field("vaccinated", "Vaccinated", "boolean")),
    "birds": (field("bird_type", "Bird Type"), field("breed", "Breed"), field("age", "Age"), field("sex", "Sex", "select", ("Male", "Female", "Pair", "Unknown")), field("cage_included", "Cage Included", "boolean")),
    "pet-food": (field("pet_type", "For Pet", "select", ("Dog", "Cat", "Bird", "Fish", "Other")), field("food_type", "Food Type", "select", ("Dry", "Wet", "Treat", "Supplement")), field("brand", "Brand"), field("package_size", "Package Size")),
    "pet-accessories": (field("pet_type", "For Pet", "select", ("Dog", "Cat", "Bird", "Fish", "Other")), field("accessory_type", "Accessory Type"), field("size", "Size"), field("material", "Material")),
    "veterinary-services": (field("service_type", "Service Type", "select", ("Consultation", "Vaccination", "Surgery", "Grooming", "Emergency", "Other")), field("animal_type", "Animal Type"), field("service_location", "Service Location", "select", ("Clinic", "Mobile", "Both")), field("emergency_service", "Emergency Service", "boolean")),
}


# Old development databases used these slugs before the current marketplace tree.
LEGACY_SLUG_ALIASES = {
    "phones": "mobile-phones",
    "laptops": "laptops-computers",
    "desktop-computers": "laptops-computers",
    "phone-accessories": "computer-accessories",
    "houses": "houses-for-sale",
    "land": "land-for-sale",
    "rentals": "houses-for-rent",
    "clothes": "mens-clothing",
    "furniture": "sofas",
    "vehicle-spare-parts": "car-parts",
}


def specs_for_slug(slug):
    return FILTER_SPECS_BY_SLUG.get(LEGACY_SLUG_ALIASES.get(slug, slug), ())
