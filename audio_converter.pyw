#! /usr/bin/env python


import logging
import os
import shutil
import StringIO
import threading
import urllib2
import zipfile

import Tkinter
import tkFileDialog
import ScrolledText

def download_lame(dest):
    lamezipurl = 'http://www.rarewares.org/files/mp3/lame3.99.5.zip'
    lamezipfh = StringIO.StringIO( urllib2.urlopen(lamezipurl).read() )
    lamezip = zipfile.ZipFile(lamezipfh)
    lamezip.extract('lame.exe', dest)


def convert_file(lame_path, src, dest):
    cmd = '%s --abr 56 -m m "%s" "%s"' % (lame_path, src, dest)
    os.system(cmd)
    

class TextHandler(logging.Handler):
    """This class allows logging to a Tkinter Text or ScrolledText widget"""
    def __init__(self, text):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Store a reference to the Text it will log to
        self.text = text

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text.configure(state='normal')
            self.text.insert(Tkinter.END, msg + '\n')
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(Tkinter.END)
        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)
        
        
class ConvertAudio:
    def __init__(self, master):
        # Entry field for the Source Directory
        destGroup = Tkinter.LabelFrame(master, text="Source Folder", padx=5, pady=5)
        destGroup.grid(row=0, column=1, sticky='WE', columnspan=7)
        Tkinter.Button(destGroup, text="Source Folder", command=self.select_srcdir).grid(row=0, column=0)
        self.sourceDir = Tkinter.StringVar()
        Tkinter.Entry(destGroup, textvariable=self.sourceDir, width=100).grid(row=0, column=1)
        
        # Configuration Options
        settingsGroup = Tkinter.LabelFrame(master, text="Settings", padx=5, pady=5)
        settingsGroup.grid(row=1, column=1, sticky='WE', columnspan=7)
        self.downloadLame = Tkinter.IntVar()
        self.downloadLame.set(1)
        self.downloadLameButton = Tkinter.Checkbutton(settingsGroup, text="Download lame.exe if not present?", variable=self.downloadLame)
        self.downloadLameButton.grid(row=0, column=0, sticky='W')
        self.overwriteExisting = Tkinter.IntVar()
        self.overwriteExistingButton = Tkinter.Checkbutton(settingsGroup, text="Overwrite existing files in destination?", variable=self.overwriteExisting)
        self.overwriteExistingButton.grid(row=1, column=0, sticky='W')
        
        # Button to launch the conversion process
        convertGroup = Tkinter.Frame(master, padx=5, pady=5)
        convertGroup.grid(row=2, column=1, sticky='WE', columnspan=7)
        self.statusLabel = Tkinter.Label(convertGroup)
        self.statusLabel.pack()
        self.convertButton = Tkinter.Button(convertGroup, text="Convert!", command=self.launch_convert)
        self.convertButton.pack()

        # Output of Status
        statusGroup = Tkinter.LabelFrame(master, text="Status", padx=5, pady=5)
        statusGroup.grid(row=3, column=1, sticky='WE', columnspan=7)
        st = ScrolledText.ScrolledText(statusGroup, state='disabled')
        st.configure(font='TkFixedFont')
        st.pack()

        # Create textLogger
        text_handler = TextHandler(st)

        # Add the handler to logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(text_handler)
        
       
    def select_srcdir(self):
        """Define the callback used to choose a file (destination)
        """
        filename = tkFileDialog.askdirectory()
        self.sourceDir.set(filename)
        return filename
        
    def get_destination(self, src_dir, full_path):
        """
        Files will be in src_dir/a...
        We need to convert that to src_dir_converted/a...
        """
        dst_path = src_dir + '_converted' + full_path.split(src_dir, 1)[1]
        return dst_path
        
    def launch_convert(self):
        threading.Thread(target=self.convert_routine).start()
    
    
    def convert_routine(self):
        # Disable Convert button during conversion
        self.convertButton.config(state="disabled")
        self.downloadLameButton.config(state="disabled")
        self.overwriteExistingButton.config(state="disabled")

        # Download LAME if not already present:
        lame_dir = os.getcwd()
        lame_path = lame_dir + os.sep + 'lame.exe'
        if not os.path.isfile(lame_path):
            if self.downloadLame.get():
                download_lame(lame_dir)
            else:
                self.statusLabel.configure(text="Error! lame.exe is not present!")
                self.downloadLameButton.config(state="normal")
                self.overwriteExistingButton .config(state="normal")
                self.convertButton.config(state="normal")
                return
                
        # Check that a source dir was configured:
        if not self.sourceDir.get():
            self.statusLabel.configure(text="Error! No source folder set!")
            self.downloadLameButton.config(state="normal")
            self.overwriteExistingButton .config(state="normal")
            self.convertButton.config(state="normal")
            return
        
        
        self.statusLabel.configure(text="Converting")
        src_dir = os.path.abspath( self.sourceDir.get() )
        self.logger.info("Counting number of files in source folder...")
        # Get the number of files, so we can display our progress
        num_files = 0
        for root, dirs, files in os.walk(src_dir):
            num_files += len(files)
        self.logger.info("There are %d files in source folder." % num_files)
        
        # Store our current position
        file_num = 0
        for root, dirs, files in os.walk(src_dir):
            for fname in files:
                srcfile = os.path.join(root,fname)
                dstfile = self.get_destination(src_dir, srcfile)
                # Skip files that already exist:
                if os.path.isfile(dstfile) and not self.overwriteExisting.get():
                    self.logger.info("Skipping %s because it already exists" % srcfile)
                    continue
                
                # Create the folder where the converted mp3 will be stored
                dstdir = os.path.dirname(dstfile)
                if not os.path.isdir(dstdir):
                    os.makedirs(dstdir)
                # Only convert audio files. Copy other files.
                if os.path.splitext(fname)[1].lower() in ['.mp3', '.wav', '.wma']:
                    self.logger.info("Converting %s to %s" % (srcfile, dstfile))
                    convert_file(lame_path, srcfile, dstfile)                
                else:
                    self.logger.info("Copying %s to %s" % (srcfile, dstfile))
                    shutil.copyfile(srcfile, dstfile)
                
        self.statusLabel.configure(text="Finished converting all files!")
        self.downloadLameButton.config(state="normal")
        self.overwriteExistingButton .config(state="normal")
        self.convertButton.config(state="normal")
        
root = Tkinter.Tk()
ConvertAudio(root)
root.mainloop()
