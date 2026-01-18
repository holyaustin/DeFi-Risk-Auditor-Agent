// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// DELIBERATE VULNERABILITY: Reentrancy Attack
contract ReentrancyVault {
    mapping(address => uint256) public balances;
    bool private locked;
    
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }
    
    // VULNERABLE: Missing reentrancy guard
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // Vulnerable: External call before state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        
        balances[msg.sender] -= amount;
    }
    
    // SAFE: With reentrancy guard
    function safeWithdraw(uint256 amount) public {
        require(!locked, "Reentrant call detected");
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        locked = true;
        balances[msg.sender] -= amount;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        locked = false;
    }
    
    function getContractBalance() public view returns (uint256) {
        return address(this).balance;
    }
}