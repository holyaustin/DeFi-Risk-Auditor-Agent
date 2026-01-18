// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// DELIBERATE VULNERABILITY: Flash loan price manipulation
contract FlashLoanPool {
    mapping(address => uint256) public balances;
    uint256 public price = 1000; // 1 token = 1000 wei
    uint256 public lastUpdate;
    
    // VULNERABLE: No time lock on price updates
    function updatePrice(uint256 newPrice) public {
        price = newPrice;
        lastUpdate = block.timestamp;
    }
    
    function flashLoan(
        uint256 amount,
        address borrower,
        bytes calldata data
    ) public returns (bool) {
        uint256 initialBalance = balances[address(this)];
        require(amount <= initialBalance, "Insufficient liquidity");
        
        // Transfer tokens to borrower
        balances[borrower] += amount;
        balances[address(this)] -= amount;
        
        // Execute borrower's operation
        (bool success, ) = borrower.call(data);
        require(success, "Flash loan execution failed");
        
        // Calculate repayment with potentially manipulated price
        uint256 repayment = (amount * price) / 1000;
        require(balances[borrower] >= repayment, "Insufficient repayment");
        
        // Return tokens
        balances[borrower] -= repayment;
        balances[address(this)] += repayment;
        
        return true;
    }
    
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }
}