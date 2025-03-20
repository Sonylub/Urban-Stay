CREATE TABLE Users (
    user_id INT PRIMARY KEY IDENTITY(1,1),
    telegram_id BIGINT NOT NULL UNIQUE,
    first_name NVARCHAR(255), 
    last_name NVARCHAR(255),
    username NVARCHAR(255),
    admin BIT DEFAULT 0
);
CREATE TABLE Rooms (
    room_id INT PRIMARY KEY IDENTITY(1,1),
    category NVARCHAR(50) NOT NULL,
    description NVARCHAR(MAX),
    price DECIMAL(10, 2) NOT NULL,
    status NVARCHAR(20) DEFAULT 'available',
    quantity INT NOT NULL,
    booked_quantity INT DEFAULT 0;
);


CREATE TABLE RoomImages (
    image_id INT PRIMARY KEY IDENTITY(1,1),
    room_id INT NOT NULL,
    image_url NVARCHAR(MAX) NOT NULL,
    FOREIGN KEY (room_id) REFERENCES Rooms(room_id)
);
CREATE TABLE Guests (
    guest_id INT PRIMARY KEY IDENTITY(1,1)
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
    FOREIGN KEY (room_id) REFERENCES Rooms(room_id),
    FOREIGN KEY (telegram_id) REFERENCES Users(telegram_id)
);
 
