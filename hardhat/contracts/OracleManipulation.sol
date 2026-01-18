// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// DELIBERATE VULNERABILITY: Oracle manipulation
contract OracleManipulation {
    address public owner;
    uint256 public price;
    
    constructor() {
        owner = msg.sender;
        price = 100 ether;
    }
    
    // VULNERABLE: Single source oracle with owner control
    function updatePrice(uint256 newPrice) public {
        require(msg.sender == owner, "Only owner can update price");
        price = newPrice;
    }
    
    function getPrice() public view returns (uint256) {
        return price;
    }
    
    // Example lending function using vulnerable oracle
    function calculateCollateral(uint256 loanAmount) public view returns (uint256) {
        return (loanAmount * 150) / price; // 150% collateralization
    }
}