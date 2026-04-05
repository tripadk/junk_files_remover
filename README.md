 # Junk File Remover System
                                                                 
  A cross-platform Python project that scans for junk files,     
  analyzes disk usage patterns, and safely cleans removable files
  by moving them to Trash instead of permanently deleting them.  
                                                                 
  This project is designed as an Operating Systems themed utility
  and demonstrates practical OS concepts such as file system     
  traversal, multithreading, multiprocessing, inter-process      
  communication (IPC), synchronization, logging, and process     
  automation.                                                    
                                                                 
  ## Features                                                    
                                                                 
  - Scan common junk-file locations on Windows and Linux         
  - Detect junk files by extension such as `.tmp`, `.log`, and   
  `.cache`                                                       
  - Analyze file count and storage usage by category             
  - Filter files by minimum age before cleanup                   
  - Safely clean junk files by moving them to Trash              
  - Detect duplicate files using SHA-256 hashing
  - Identify large files based on a configurable threshold       
  - Show hidden files found during scanning                      
  - Maintain cleanup logs for audit and review
  - Support Linux-only utilities such as:                        
    - disk usage reporting                                       
    - disk space monitoring                                      
    - running process listing                                    
    - cron-based auto-clean scheduling

  ## OS Concepts Used                                            
                                                                 
  This project was built to demonstrate core Operating System    
  concepts in a practical way:                                   
                                                                 
  - **File System Management**: scans directories, checks file   
  metadata, and classifies junk files                            
  - **Multithreading**: uses threads to scan multiple approved   
  directories in parallel                                        
  - **Multiprocessing and IPC**: uses a background cleaner       
  process with a queue for communication                         
  - **Synchronization**: uses locks to safely update shared scan 
  results                                                        
  - **Process Management**: Linux process monitoring with system 
  commands                                                       
  - **Scheduling**: Linux cron integration for automatic cleanup 
  - **Logging**: records cleanup activity and errors in          
  `cleaner.log`                                                  
                                                                 
  ## Project Structure                                           
                                                                 
  ```text                                                        
  junk_file_remover/                                             
  ├── main.py                                                    
  ├── scanner.py                                                 
  ├── cleaner.py                                                 
  ├── analyzer.py                                                
  ├── duplicate_finder.py                                        
  ├── large_file_finder.py                                       
  ├── config_loader.py                                           
  ├── log_viewer.py                                              
  ├── linux_disk_usage.py                                        
  ├── linux_disk_space.py                                        
  ├── linux_process_monitor.py                                   
  ├── linux_scheduler.py                                         
  ├── utils.py                                                   
  ├── config.json                                                
  ├── cleaner.log                                                
  └── Trash/                                                     
                                                                 
  ## How It Works                                                
                                                                 
  1. The scanner checks only approved safe directories.          
  2. Junk files are identified by configured extensions.         
  3. File metadata such as size, age, and hidden status is       
     collected.                                                  
  4. The analyzer summarizes the scan results.                   
  5. During cleanup, eligible files are moved to Trash instead of
     being permanently deleted.                                  
  6. All cleanup operations are logged for later review.         
                                                                 
  ## Configuration                                               
                                                                 
  The project uses a config.json file for runtime settings.      
                                                                 
  Example configuration:                                         

  {                                                              
    "junk_extensions": [".tmp", ".log", ".cache"],               
    "min_age_days": 7,                                           
    "large_file_threshold_mb": 100,                              
    "demo_mode": true,                                           
    "include_hidden_files": true                                 
  }                                                              
                                                                 
  ### Configuration Fields                                       
                                                                 
  - junk_extensions: file types treated as junk                  
  - min_age_days: minimum file age required before cleanup       
  - large_file_threshold_mb: threshold for reporting large files 
  - demo_mode: enables safe limited execution for testing        
  - include_hidden_files: includes hidden files in scan results  
                                                                 
  ## Usage
### Run on Linux:                                                     
 python3 main.py

### Run on Windows:
python main.py                                               
  The program opens a menu-driven interface with options to:     
                                                                 
  - scan the system                                              
  - analyze junk files                                           
  - clean junk files                                             
  - find duplicate files                                         
  - find large files                                             
  - show hidden files                                            
  - view logs                                                    
  - access Linux-only monitoring features                        

  ## Safety Features                                             
                                                                 
  - Only scans approved safe directories                         
  - Skips protected system locations                             
  - Checks file permissions before cleanup
  - Moves files to Trash instead of deleting them permanently    
  - Supports demo mode for safer testing                         
                                                                 
  ## Output and Logs                                             
                                                                 
  - Cleanup activity is stored in cleaner.log                    
  - Moved files are placed in the Trash folder on Windows        
  - On Linux, files are moved to the user Trash location         
                                                                 
  ## Future Improvements                                         
                                                                 
  - GUI version of the utility                                   
  - Restore files from Trash                                     
  - More file-type categories                                    
  - Scheduled cleanup support for Windows                        
  - Export scan reports to CSV or JSON                           
                                                                 
  ## Conclusion                                                  
                                                                 
  The Junk File Remover System is a practical Python-based OS    
  project that combines safe file cleanup with important         
  operating system concepts. It is useful both as a learning     
  project and as a basic system maintenance tool.       
