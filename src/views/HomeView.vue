<script setup lang="ts">
import '../assets/style.css'



</script>

<template>
  <main>
    <div class="full-page">
      <div class="content-holder">
        <div class="title">
          Kevin Steve Sathyanath
        </div>
      </div>
    </div>
  </main> 
</template>


<style>

@import url('https://fonts.googleapis.com/css2?family=Corben:wght@400;700&display=swap');

.full-page {
  background-color: var(--background-colour);
  color: var(--headings-colour);
  height:100vh;
  display: flex;
}

.content-holder {
  width: 100%;
  margin: 2rem;
}

.title{
  font-family: "Corben", serif;
  font-weight: 900;
  font-style: normal;
  font-size: xx-large
}

.corben-regular {
  font-family: "Corben", serif;
  font-weight: 400;
  font-style: normal;
}

.corben-bold {
  font-family: "Corben", serif;
  font-weight: 700;
  font-style: normal;
}
</style>
