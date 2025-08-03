-- Create Database (run this first in SQL Server Management Studio)
CREATE DATABASE FaceDB;
GO

USE [FaceDB]
GO

-- Create User table
CREATE TABLE [dbo].[User](
    [Id] [int] IDENTITY(1,1) NOT NULL,
    [Email] [nvarchar](255) NOT NULL,
    [Password] [nvarchar](255) NOT NULL,
    [Type] [nvarchar](50) NOT NULL,
    CONSTRAINT [PK_User] PRIMARY KEY CLUSTERED ([Id] ASC)
)
GO

-- Create Contractor table
CREATE TABLE [dbo].[Contractor](
    [Id] [int] IDENTITY(1,1) NOT NULL,
    [Name] [nvarchar](255) NOT NULL,
    [FatherName] [nvarchar](255) NOT NULL,
    [Address] [nvarchar](500) NULL,
    [IsActive] [bit] NOT NULL DEFAULT(1),
    CONSTRAINT [PK_Contractor] PRIMARY KEY CLUSTERED ([Id] ASC)
)
GO

-- Create Employee table
CREATE TABLE [dbo].[Employee](
    [Id] [int] IDENTITY(1,1) NOT NULL,
    [Name] [nvarchar](255) NOT NULL,
    [FatherName] [nvarchar](255) NOT NULL,
    [PhoneNo] [nvarchar](20) NULL,
    [Address] [nvarchar](500) NULL,
    [ContractorId] [int] NULL,
    [IsActive] [bit] NOT NULL DEFAULT(1),
    CONSTRAINT [PK_Employee] PRIMARY KEY CLUSTERED ([Id] ASC),
    CONSTRAINT [FK_Employee_Contractor] FOREIGN KEY([ContractorId]) 
        REFERENCES [dbo].[Contractor] ([Id])
)
GO

-- Insert sample data
-- Sample Users
INSERT INTO [User] (Email, Password, Type) VALUES 
('admin@company.com', 'admin123', 'admin'),
('hr@company.com', 'hr123', 'hr');

-- Sample Contractors
INSERT INTO [Contractor] (Name, FatherName, Address, IsActive) VALUES 
('ABC Construction', 'N/A', '123 Main St', 1),
('XYZ Services', 'N/A', '456 Oak Ave', 1);

-- Sample Employees
INSERT INTO [Employee] (Name, FatherName, PhoneNo, Address, ContractorId, IsActive) VALUES 
('John Doe', 'Richard Doe', '555-0123', '789 Pine St', 1, 1),
('Jane Smith', 'Robert Smith', '555-0124', '321 Elm St', 2, 1),
('Mike Johnson', 'David Johnson', '555-0125', '654 Maple Ave', NULL, 1);

-- Create indexes for better performance
CREATE INDEX IX_Employee_ContractorId ON Employee(ContractorId);
CREATE INDEX IX_User_Email ON [User](Email);
GO