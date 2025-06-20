import customtkinter as ctk
import tkinter as tk
from tkinter import colorchooser, font, messagebox
from datetime import datetime, time
import json
import os
import threading
import time as time_module
import winsound
import sys

# CustomTkinter sozlamalari
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class NotebookApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("📒 Do'kon Eslatma Dasturi")
        self.root.state("zoomed")
        
        # JSON fayl yo'li
        self.data_file = "notebook_data.json"
        self.load_data()
        
        # Budilnik thread
        self.alarm_thread = None
        self.alarm_running = False
        
        self.setup_ui()
        self.start_alarm_checker()
        
    def load_data(self):
        """JSON fayldan ma'lumotlarni yuklash"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            else:
                self.data = {"notes": [], "alarms": []}
        except:
            self.data = {"notes": [], "alarms": []}
    
    def save_data(self):
        """JSON faylga ma'lumotlarni saqlash"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            messagebox.showerror("saqlandi", "saqlandi")
        except Exception as e:
            messagebox.showerror("Xato", f"Ma'lumotlarni saqlashda xato: {str(e)}")
    
    def setup_ui(self):
        """Foydalanuvchi interfeysini sozlash"""
        
        # Asosiy frame
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Sarlavha
        title_label = ctk.CTkLabel(
            main_frame, 
            text="📒 Do'kon Eslatma Dasturi", 
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=(20, 10))
        
        # Tugmalar paneli
        self.setup_button_panel(main_frame)
        
        # Text maydon
        self.setup_text_area(main_frame)
        
        # Pastki panel (budilnik va holat)
        self.setup_bottom_panel(main_frame)
        
    def setup_button_panel(self, parent):
        """Tugmalar panelini sozlash"""
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        # Birinchi qator tugmalar
        row1_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        row1_frame.pack(fill="x", pady=5)
        
        buttons_row1 = [
            ("🆕 Yangi Eslatma", self.new_note),
            ("💾 Saqlash", self.auto_save),
            ("📂 Saqlangan Fayllar", self.show_saved_files),
            ("🧹 Tozalash", self.clear_text)
        ]
        
        for text, command in buttons_row1:
            btn = ctk.CTkButton(
                row1_frame, 
                text=text, 
                command=command,
                width=180,
                height=40,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            btn.pack(side="left", padx=5, expand=True, fill="x")
        
        # Ikkinchi qator tugmalar
        row2_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        row2_frame.pack(fill="x", pady=5)
        
        buttons_row2 = [
            ("🎨 Rang", self.choose_color),
            ("🖋 Shrift", self.choose_font),
            ("⏰ Budilnik", self.set_alarm),
            ("📋 Budilniklar", self.show_alarms)
        ]
        
        for text, command in buttons_row2:
            btn = ctk.CTkButton(
                row2_frame, 
                text=text, 
                command=command,
                width=180,
                height=40,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            btn.pack(side="left", padx=5, expand=True, fill="x")
    
    def setup_text_area(self, parent):
        """Matn maydonini sozlash"""
        text_frame = ctk.CTkFrame(parent)
        text_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Text widget
        self.text_area = tk.Text(
            text_frame,
            wrap="word",
            font=("Arial", 14),
            undo=True,
            bg="#212121",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#1f538d"
        )
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(text_frame, command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=scrollbar.set)
        
        self.text_area.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)
        
        # Avtomatik sana qo'shish
        self.add_today_date()
    
    def setup_bottom_panel(self, parent):
        """Pastki panelni sozlash"""
        bottom_frame = ctk.CTkFrame(parent)
        bottom_frame.pack(fill="x", padx=20, pady=10)
        
        # Holat labeli
        self.status_label = ctk.CTkLabel(
            bottom_frame,
            text="✅ Tayyor",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=10, pady=10)
        
        # Vaqt labeli
        self.time_label = ctk.CTkLabel(
            bottom_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.time_label.pack(side="right", padx=10, pady=10)
        
        # Vaqtni yangilash
        self.update_time()
    
    def update_time(self):
        """Vaqtni yangilash"""
        current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        self.time_label.configure(text=f"🕓 {current_time}")
        self.root.after(1000, self.update_time)
    
    def add_today_date(self):
        """Bugungi sanani qo'shish"""
        now = datetime.now().strftime("%d-%m-%Y %H:%M")
        self.text_area.insert("end", f"📅 {now}\n" + "="*50 + "\n\n")
        self.text_area.see("end")
    
    def new_note(self):
        """Yangi eslatma"""
        if self.text_area.get(1.0, "end-1c").strip():
            if messagebox.askyesno("Yangi Eslatma", "Joriy matnni saqlab, yangi eslatma boshlansinmi?"):
                self.auto_save()
                self.text_area.delete(1.0, "end")
                self.add_today_date()
        else:
            self.text_area.delete(1.0, "end")
            self.add_today_date()
    
    def choose_color(self):
        """Rangni tanlash"""
        color = colorchooser.askcolor()[1]
        if color:
            self.text_area.config(fg=color)
            self.status_label.configure(text=f"🎨 Rang o'zgartirildi: {color}")
    
    def choose_font(self):
        """Shriftni tanlash"""
        font_window = ctk.CTkToplevel(self.root)
        font_window.title("🖋 Shrift tanlash")
        font_window.state("zoomed")
        
        # Shriftlar ro'yxati
        fonts = list(font.families())
        fonts.sort()
        
        # Shrift tanlash
        font_frame = ctk.CTkFrame(font_window)
        font_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(font_frame, text="Shrift tanlang:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Shrift ro'yxati
        font_listbox = tk.Listbox(font_frame, height=15)
        font_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        for f in fonts:
            font_listbox.insert("end", f)
        
        # O'lcham tanlash
        size_frame = ctk.CTkFrame(font_frame)
        size_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(size_frame, text="O'lcham:").pack(side="left", padx=5)
        size_var = ctk.StringVar(value="14")
        size_entry = ctk.CTkEntry(size_frame, textvariable=size_var, width=60)
        size_entry.pack(side="left", padx=5)
        
        def apply_font():
            try:
                selection = font_listbox.curselection()
                if selection:
                    selected_font = font_listbox.get(selection[0])
                    font_size = int(size_var.get())
                    self.text_area.config(font=(selected_font, font_size))
                    self.status_label.configure(text=f"🖋 Shrift: {selected_font} ({font_size})")
                    font_window.destroy()
            except:
                messagebox.showerror("Xato", "Yaroqli shrift o'lchamini kiriting")
        
        ctk.CTkButton(font_frame, text="Qo'llash", command=apply_font).pack(pady=10)
    
    def auto_save(self):
        """Avtomatik saqlash"""
        content = self.text_area.get(1.0, "end-1c")
        if content.strip():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            note_data = {
                "id": timestamp,
                "title": f"Eslatma {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                "content": content,
                "created": timestamp
            }
            
            self.data["notes"].append(note_data)
            self.save_data()
            self.status_label.configure(text="💾 Avtomatik saqlandi!")
            
            # 3 soniyadan keyin holatni qaytarish
            self.root.after(3000, lambda: self.status_label.configure(text="✅ Tayyor"))
        else:
            messagebox.showwarning("Ogohlantirish", "Saqlanadigan matn yo'q!")
    
    def show_saved_files(self):
        """Saqlangan fayllarni ko'rsatish"""
        if not self.data["notes"]:
            messagebox.showinfo("Ma'lumot", "Hech qanday saqlangan eslatma yo'q!")
            return
        
        files_window = ctk.CTkToplevel(self.root)
        files_window.title("📂 Saqlangan Eslatmalar")
        files_window.state("zoomed")
        
        # Ro'yxat frame
        list_frame = ctk.CTkFrame(files_window)
        list_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(list_frame, text="📂 Saqlangan Eslatmalar", 
                    font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        
        # Eslatmalar ro'yxati
        notes_frame = ctk.CTkScrollableFrame(list_frame)
        notes_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        for note in reversed(self.data["notes"]):  # Eng yangilarini birinchi ko'rsatish
            note_frame = ctk.CTkFrame(notes_frame)
            note_frame.pack(fill="x", pady=5)
            
            # Sarlavha va sana
            title_label = ctk.CTkLabel(
                note_frame, 
                text=note["title"], 
                font=ctk.CTkFont(size=14, weight="bold")
            )
            title_label.pack(anchor="w", padx=10, pady=5)
            
            # Kontent preview
            preview = note["content"][:100] + "..." if len(note["content"]) > 100 else note["content"]
            preview_label = ctk.CTkLabel(note_frame, text=preview, justify="left")
            preview_label.pack(anchor="w", padx=10)
            
            # Tugmalar
            btn_frame = ctk.CTkFrame(note_frame, fg_color="transparent")
            btn_frame.pack(fill="x", padx=10, pady=5)
            
            open_btn = ctk.CTkButton(
                btn_frame, 
                text="Ochish", 
                command=lambda n=note: self.open_note(n, files_window),
                width=80,
                height=30
            )
            open_btn.pack(side="left", padx=5)
            
            delete_btn = ctk.CTkButton(
                btn_frame, 
                text="O'chirish", 
                command=lambda n=note: self.delete_note(n, files_window),
                width=80,
                height=30,
                fg_color="red",
                hover_color="darkred"
            )
            delete_btn.pack(side="left", padx=5)
    
    def open_note(self, note, parent_window):
        """Eslatmani ochish"""
        if messagebox.askyesno("Eslatmani ochish", "Joriy matnni saqlab, tanlangan eslatmani ochishni xohlaysizmi?"):
            current_content = self.text_area.get(1.0, "end-1c")
            if current_content.strip():
                self.auto_save()
            
            self.text_area.delete(1.0, "end")
            self.text_area.insert(1.0, note["content"])
            parent_window.destroy()
            self.status_label.configure(text=f"📂 Ochildi: {note['title']}")
    
    def delete_note(self, note, parent_window):
        """Eslatmani o'chirish"""
        if messagebox.askyesno("O'chirish", f"'{note['title']}' eslatmasini o'chirishni xohlaysizmi?"):
            self.data["notes"] = [n for n in self.data["notes"] if n["id"] != note["id"]]
            self.save_data()
            parent_window.destroy()
            self.show_saved_files()  # Ro'yxatni yangilash
            self.status_label.configure(text="🗑 Eslatma o'chirildi")
    
    def clear_text(self):
        """Matnni tozalash"""
        if messagebox.askyesno("Ogohlantirish", "Barcha matnni o'chirishni xohlaysizmi?"):
            self.text_area.delete(1.0, "end")
            self.status_label.configure(text="🧹 Tozalandi")
    
    def set_alarm(self):
        """Budilnik o'rnatish"""
        alarm_window = ctk.CTkToplevel(self.root)
        alarm_window.title("⏰ Budilnik O'rnatish")
        alarm_window.state("zoomed")
        
        main_frame = ctk.CTkFrame(alarm_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="⏰ Budilnik O'rnatish", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Vaqt tanlash
        time_frame = ctk.CTkFrame(main_frame)
        time_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(time_frame, text="Vaqt (HH:MM):").pack(pady=5)
        
        time_input_frame = ctk.CTkFrame(time_frame, fg_color="transparent")
        time_input_frame.pack()
        
        hour_var = ctk.StringVar(value="12")
        minute_var = ctk.StringVar(value="00")
        
        hour_entry = ctk.CTkEntry(time_input_frame, textvariable=hour_var, width=50)
        hour_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(time_input_frame, text=":").pack(side="left")
        
        minute_entry = ctk.CTkEntry(time_input_frame, textvariable=minute_var, width=50)
        minute_entry.pack(side="left", padx=5)
        
        # Eslatma matni
        message_frame = ctk.CTkFrame(main_frame)
        message_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(message_frame, text="Eslatma matni:").pack(pady=5)
        message_var = ctk.StringVar(value="Eslatma vaqti!")
        message_entry = ctk.CTkEntry(message_frame, textvariable=message_var, width=250)
        message_entry.pack(pady=5)
        
        def save_alarm():
            try:
                hour = int(hour_var.get())
                minute = int(minute_var.get())
                
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    alarm_time = f"{hour:02d}:{minute:02d}"
                    alarm_data = {
                        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
                        "time": alarm_time,
                        "message": message_var.get(),
                        "active": True
                    }
                    
                    self.data["alarms"].append(alarm_data)
                    self.save_data()
                    
                    messagebox.showinfo("Muvaffaqiyat", f"Budilnik {alarm_time} ga o'rnatildi!")
                    alarm_window.destroy()
                    self.status_label.configure(text=f"⏰ Budilnik: {alarm_time}")
                else:
                    messagebox.showerror("Xato", "Yaroqli vaqt kiriting! (00:00 - 23:59)")
            except ValueError:
                messagebox.showerror("Xato", "Faqat raqam kiriting!")
        
        ctk.CTkButton(main_frame, text="Budilnik O'rnatish", command=save_alarm).pack(pady=20)
    
    def show_alarms(self):
        """Budilniklarni ko'rsatish"""
        if not self.data["alarms"]:
            messagebox.showinfo("Ma'lumot", "Hech qanday budilnik o'rnatilmagan!")
            return
        
        alarms_window = ctk.CTkToplevel(self.root)
        alarms_window.title("📋 Budilniklar")
        alarms_window.state("zoomed")
        
        main_frame = ctk.CTkFrame(alarms_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="📋 O'rnatilgan Budilniklar", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        alarms_frame = ctk.CTkScrollableFrame(main_frame)
        alarms_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        for alarm in self.data["alarms"]:
            alarm_frame = ctk.CTkFrame(alarms_frame)
            alarm_frame.pack(fill="x", pady=5)
            
            # Budilnik ma'lumotlari
            info_frame = ctk.CTkFrame(alarm_frame, fg_color="transparent")
            info_frame.pack(fill="x", padx=10, pady=5)
            
            time_label = ctk.CTkLabel(
                info_frame, 
                text=f"⏰ {alarm['time']}", 
                font=ctk.CTkFont(size=16, weight="bold")
            )
            time_label.pack(side="left")
            
            status_text = "🟢 Faol" if alarm["active"] else "🔴 O'chiq"
            status_label = ctk.CTkLabel(info_frame, text=status_text)
            status_label.pack(side="right")
            
            message_label = ctk.CTkLabel(alarm_frame, text=f"📝 {alarm['message']}")
            message_label.pack(anchor="w", padx=10)
            
            # Tugmalar
            btn_frame = ctk.CTkFrame(alarm_frame, fg_color="transparent")
            btn_frame.pack(fill="x", padx=10, pady=5)
            
            toggle_text = "O'chirish" if alarm["active"] else "Yoqish"
            toggle_btn = ctk.CTkButton(
                btn_frame, 
                text=toggle_text, 
                command=lambda a=alarm: self.toggle_alarm(a, alarms_window),
                width=80,
                height=30
            )
            toggle_btn.pack(side="left", padx=5)
            
            delete_btn = ctk.CTkButton(
                btn_frame, 
                text="O'chirish", 
                command=lambda a=alarm: self.delete_alarm(a, alarms_window),
                width=80,
                height=30,
                fg_color="red",
                hover_color="darkred"
            )
            delete_btn.pack(side="left", padx=5)
    
    def toggle_alarm(self, alarm, parent_window):
        """Budilnikni yoqish/o'chirish"""
        for a in self.data["alarms"]:
            if a["id"] == alarm["id"]:
                a["active"] = not a["active"]
                break
        
        self.save_data()
        parent_window.destroy()
        self.show_alarms()
    
    def delete_alarm(self, alarm, parent_window):
        """Budilnikni o'chirish"""
        if messagebox.askyesno("O'chirish", f"'{alarm['time']}' budilnikni o'chirishni xohlaysizmi?"):
            self.data["alarms"] = [a for a in self.data["alarms"] if a["id"] != alarm["id"]]
            self.save_data()
            parent_window.destroy()
            self.show_alarms()
    
    def start_alarm_checker(self):
        """Budilnik tekshiruvchisini ishga tushirish"""
        def check_alarms():
            while True:
                try:
                    current_time = datetime.now().strftime("%H:%M")
                    
                    for alarm in self.data["alarms"]:
                        if alarm["active"] and alarm["time"] == current_time:
                            # Budilnik tovushini chiqarish
                            threading.Thread(target=self.play_alarm_sound, daemon=True).start()
                            
                            # Xabar ko'rsatish
                            self.root.after(0, lambda: self.show_alarm_message(alarm))
                            
                            # Budilnikni o'chirish (bir marta ishlashi uchun)
                            alarm["active"] = False
                            self.save_data()
                    
                    time_module.sleep(60)  # Har daqiqada tekshirish
                except:
                    pass
        
        alarm_thread = threading.Thread(target=check_alarms, daemon=True)
        alarm_thread.start()
    
    def play_alarm_sound(self):
        """Budilnik tovushini chiqarish"""
        try:
            # Windows uchun system sound
            for _ in range(5):  # 5 marta tovush chiqarish
                winsound.Beep(1000, 500)  # 1000Hz, 500ms
                time_module.sleep(0.5)
        except:
            # Agar winsound ishlamasa, print qilish
            print("🔔 BUDILNIK! 🔔")
    
    def show_alarm_message(self, alarm):
        """Budilnik xabarini ko'rsatish"""
        messagebox.showinfo("⏰ BUDILNIK!", f"🔔 {alarm['message']}\n\nVaqt: {alarm['time']}")
    
    def run(self):
        """Dasturni ishga tushirish"""
        self.root.mainloop()

# Dasturni ishga tushirish
if __name__ == "__main__":
    app = NotebookApp()
    app.run()