-- Таблица Users
CREATE TABLE Users (
    user_id INT PRIMARY KEY IDENTITY(1,1),
    telegram_id BIGINT NOT NULL UNIQUE,
    first_name NVARCHAR(255), 
    last_name NVARCHAR(255),
    username NVARCHAR(255),
    admin BIT DEFAULT 0
);

-- Таблица Rooms
CREATE TABLE Rooms (
    room_id INT PRIMARY KEY IDENTITY(1,1),
    category NVARCHAR(50) NOT NULL,
    description NVARCHAR(MAX),
    price DECIMAL(10, 2) NOT NULL,
    status NVARCHAR(20) DEFAULT 'available',
    quantity INT NOT NULL,
    booked_quantity INT DEFAULT 0,
    CONSTRAINT CHK_RoomQuantity CHECK (booked_quantity <= quantity)
);

-- Таблица RoomImages
CREATE TABLE RoomImages (
    image_id INT PRIMARY KEY IDENTITY(1,1),
    room_id INT NOT NULL,
    image_url NVARCHAR(MAX) NOT NULL,
    FOREIGN KEY (room_id) REFERENCES Rooms(room_id) ON DELETE CASCADE
);

-- Таблица Guests
CREATE TABLE Guests (
    guest_id INT PRIMARY KEY IDENTITY(1,1),
    room_id INT NOT NULL,
    telegram_id BIGINT NOT NULL,
    first_name NVARCHAR(255) NOT NULL,
    last_name NVARCHAR(255) NOT NULL,
    email NVARCHAR(255),
    phone NVARCHAR(20),
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    comment NVARCHAR(MAX),
    booking_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (room_id) REFERENCES Rooms(room_id) ON DELETE CASCADE,
    FOREIGN KEY (telegram_id) REFERENCES Users(telegram_id) ON DELETE CASCADE,
    CONSTRAINT CHK_CheckInOutDates CHECK (check_out_date > check_in_date)
);

-- Таблица Employees
CREATE TABLE Employees (
    employee_id INT PRIMARY KEY IDENTITY(1,1),
    full_name NVARCHAR(255) NOT NULL,
    position NVARCHAR(100) NOT NULL,
    contact_phone NVARCHAR(20) NOT NULL,
    work_email NVARCHAR(255) NOT NULL
);

-- Таблица Reviews
CREATE TABLE Reviews (
    review_id INT PRIMARY KEY IDENTITY(1,1),
    guest_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment NVARCHAR(500),
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (guest_id) REFERENCES Guests(guest_id) ON DELETE CASCADE
);

-- Таблица Services
CREATE TABLE Services (
    service_id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(100) NOT NULL UNIQUE,
    price DECIMAL(10,2) NOT NULL,
    short_description NVARCHAR(150),
    detailed_description NVARCHAR(MAX) NULL
);

-- Доп. таблица для связи Guests и Services (если нужно отслеживать заказы услуг)
CREATE TABLE GuestServices (
    guest_id INT NOT NULL,
    service_id INT NOT NULL,
    quantity INT DEFAULT 1 CHECK (quantity > 0),
    order_date DATETIME DEFAULT GETDATE(),
    status NVARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'canceled')),
    employee_id INT NULL,
    PRIMARY KEY (guest_id, service_id, order_date),
    FOREIGN KEY (guest_id) REFERENCES Guests(guest_id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES Services(service_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES Employees(employee_id) ON DELETE SET NULL
);
GO

CREATE VIEW GuestServicesWithPrice AS
SELECT gs.*, s.price * gs.quantity AS total_price
FROM GuestServices gs
JOIN Services s ON gs.service_id = s.service_id;

