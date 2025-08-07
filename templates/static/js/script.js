//----------------------------------------------------------------Login Page
 function login(event) {
      event.preventDefault();
      const id = document.getElementById('loginID').value;
      const pass = document.getElementById('loginPassword').value;

      // FOR TESTING PURPOSES: Allow any input to pass
      if (id && pass) {
        alert('Login successful!');
        window.location.href = 'index.html';
      } else {
        alert('Please enter both ID and Password');
      }
    }





    //-----------------------------------------------------------Singup page
  function signup(event) {
    event.preventDefault();

    const id = document.getElementById('EmpId').value;
    const name = document.getElementById('EmpName').value;
    const father = document.getElementById('FatherName').value;
    const address = document.getElementById('Address').value;
    const date = document.getElementById('EmpDate').value;
    const contractor = document.getElementById('ContractorName').value;
    const picture = document.getElementById('EmpPicture').files[0];
    const isActive = document.getElementById('Active').checked;


    if (!picture) {
      alert("Please upload a picture.");
      return;
    }

    if (localStorage.getItem(id)) {
      alert('This employee already exists.');
      return;
    }

    const reader = new FileReader();
    reader.onload = function () {
      const pictureData = reader.result;

      const employee = {
        id,
        name,
        father,
        address,
        date,
        contractor,
        picture: pictureData,

      };

      localStorage.setItem(id, JSON.stringify(employee));
      alert('Signup successful!');
      

    };

    reader.readAsDataURL(picture);
  }

  //------------------------------------------------------------------------Table COde...
window.onload = function () {
  const tableBody = document.getElementById('employeeTableBody');
  const uploadInput = document.getElementById('uploadFile');

  if (!tableBody || !uploadInput) return;

  // Excel file upload handler
  uploadInput.addEventListener('change', function (e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (event) {
      const data = new Uint8Array(event.target.result);
      const workbook = XLSX.read(data, { type: 'array' });

      const sheetName = workbook.SheetNames[0];
      const sheet = workbook.Sheets[sheetName];
      const json = XLSX.utils.sheet_to_json(sheet);

      tableBody.innerHTML = '';

      json.forEach((emp, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${emp.ID || ''}</td>
          <td>${emp.Name || ''}</td>
          <td>${emp["Email Address"] || ''}</td>
          <td>${emp.Salary || 0}</td>
          <td><input type="checkbox" ${emp.Paid === "☑" ? "checked" : ""}></td>
        `;
        tableBody.appendChild(row);
      });
    };

    reader.readAsArrayBuffer(file);
  });
};



// Call the dataTables jQuery plugin
$(document).ready(function() {
  $('#dataTable').DataTable();
});


(function($) {
  "use strict"; // Start of use strict

  // Toggle the side navigation
  $("#sidebarToggle, #sidebarToggleTop").on('click', function(e) {
    $("body").toggleClass("sidebar-toggled");
    $(".sidebar").toggleClass("toggled");
    if ($(".sidebar").hasClass("toggled")) {
      $('.sidebar .collapse').collapse('hide');
    };
  });

  // Close any open menu accordions when window is resized below 768px
  $(window).resize(function() {
    if ($(window).width() < 768) {
      $('.sidebar .collapse').collapse('hide');
    };
    
    // Toggle the side navigation when window is resized below 480px
    if ($(window).width() < 480 && !$(".sidebar").hasClass("toggled")) {
      $("body").addClass("sidebar-toggled");
      $(".sidebar").addClass("toggled");
      $('.sidebar .collapse').collapse('hide');
    };
  });

  // Prevent the content wrapper from scrolling when the fixed side navigation hovered over
  $('body.fixed-nav .sidebar').on('mousewheel DOMMouseScroll wheel', function(e) {
    if ($(window).width() > 768) {
      var e0 = e.originalEvent,
        delta = e0.wheelDelta || -e0.detail;
      this.scrollTop += (delta < 0 ? 1 : -1) * 30;
      e.preventDefault();
    }
  });

  // Scroll to top button appear
  $(document).on('scroll', function() {
    var scrollDistance = $(this).scrollTop();
    if (scrollDistance > 100) {
      $('.scroll-to-top').fadeIn();
    } else {
      $('.scroll-to-top').fadeOut();
    }
  });

  // Smooth scrolling using jQuery easing
  $(document).on('click', 'a.scroll-to-top', function(e) {
    var $anchor = $(this);
    $('html, body').stop().animate({
      scrollTop: ($($anchor.attr('href')).offset().top)
    }, 1000, 'easeInOutExpo');
    e.preventDefault();
  });

})(jQuery); // End of use strict


